from datetime import timedelta

import pytest

from app.modules.auth.entities.password_policy import PasswordTooCommonError
from app.modules.auth.entities.user import User
from app.modules.auth.entities.user_session import ClientPlatform
from app.modules.auth.use_cases.errors import ExpiredLinkError, InvalidLinkError
from app.modules.auth.use_cases.log_in import LogInInput
from app.modules.auth.use_cases.password_reset_mailer import PASSWORD_RESET_LIFETIME
from app.modules.auth.use_cases.ports import TokenPurpose
from app.modules.auth.use_cases.reset_password import ResetPasswordInput
from tests.modules.auth.use_cases.conftest import PASSWORD, AuthKit

NEW_PASSWORD = "otra frase larga y nueva"


def _link(kit: AuthKit, user: User) -> str:
    return kit.reset_tokens.create(
        user.id, user.password_changed_at, PASSWORD_RESET_LIFETIME, kit.clock()
    )


def _reset(kit: AuthKit, token: str, password: str = NEW_PASSWORD) -> None:
    kit.reset_password().execute(ResetPasswordInput(token, password))


def test_guarda_la_nueva_y_cierra_todas_las_sesiones(kit: AuthKit) -> None:
    user = kit.add_user()
    for platform in (ClientPlatform.ANDROID, ClientPlatform.WEB):
        kit.log_in().execute(LogInInput("ana.rios", PASSWORD, platform, None))

    _reset(kit, _link(kit, user))

    saved = kit.users.get(user.id)
    assert saved is not None
    assert saved.password_hash == kit.hasher.hash(NEW_PASSWORD)
    assert saved.password_changed_at == kit.clock()
    assert all(s.revoked_at is not None for s in kit.sessions.sessions.values())


def test_el_enlace_sirve_una_sola_vez(kit: AuthKit) -> None:
    user = kit.add_user()
    token = _link(kit, user)
    _reset(kit, token)

    with pytest.raises(InvalidLinkError):
        _reset(kit, token, "una tercera frase larga")


def test_un_enlace_viejo_no_sirve_si_la_contrasena_ya_cambio(kit: AuthKit) -> None:
    user = kit.add_user()
    old_link = _link(kit, user)
    kit.clock.advance(timedelta(minutes=1))
    _reset(kit, _link(kit, user))

    with pytest.raises(InvalidLinkError):
        _reset(kit, old_link, "una tercera frase larga")


def test_enlace_vencido(kit: AuthKit) -> None:
    user = kit.add_user()
    token = _link(kit, user)
    kit.clock.advance(timedelta(minutes=30))

    with pytest.raises(ExpiredLinkError):
        _reset(kit, token)


def test_enlace_de_verificacion_no_sirve_para_recuperar(kit: AuthKit) -> None:
    user = kit.add_user()
    verify = kit.email_links.create(
        user.id, TokenPurpose.VERIFY_EMAIL, timedelta(hours=1), kit.clock()
    )

    with pytest.raises(InvalidLinkError):
        _reset(kit, verify)


def test_contrasena_comun_no_cambia_nada(kit: AuthKit) -> None:
    user = kit.add_user()

    with pytest.raises(PasswordTooCommonError):
        _reset(kit, _link(kit, user), "Password")
    assert kit.unit_of_work.commits == 0
