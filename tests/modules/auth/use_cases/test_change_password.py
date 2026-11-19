import pytest

from app.modules.auth.entities.password_policy import PasswordLengthError
from app.modules.auth.entities.user_session import ClientPlatform
from app.modules.auth.use_cases.change_password import ChangePasswordInput
from app.modules.auth.use_cases.errors import CurrentPasswordIncorrectError
from app.modules.auth.use_cases.log_in import LogInInput
from tests.modules.auth.use_cases.conftest import PASSWORD, AuthKit

NEW_PASSWORD = "otra frase larga y nueva"


def _open_two_sessions(kit: AuthKit) -> None:
    for platform in (ClientPlatform.ANDROID, ClientPlatform.WEB):
        kit.log_in().execute(LogInInput("ana.rios", PASSWORD, platform, None))


def _revoked(kit: AuthKit) -> list[bool]:
    return [s.revoked_at is not None for s in kit.sessions.sessions.values()]


def test_guarda_la_nueva_y_cierra_todas_las_sesiones(kit: AuthKit) -> None:
    user = kit.add_user()
    _open_two_sessions(kit)

    kit.change_password().execute(ChangePasswordInput(user.id, PASSWORD, NEW_PASSWORD))

    saved = kit.users.get(user.id)
    assert saved is not None
    assert saved.password_hash == kit.hasher.hash(NEW_PASSWORD)
    assert saved.password_changed_at == kit.clock()
    assert _revoked(kit) == [True, True]


def test_contrasena_actual_incorrecta_no_cambia_nada(kit: AuthKit) -> None:
    user = kit.add_user()
    _open_two_sessions(kit)
    commits_before = kit.unit_of_work.commits

    with pytest.raises(CurrentPasswordIncorrectError):
        kit.change_password().execute(
            ChangePasswordInput(user.id, "otra cosa", NEW_PASSWORD)
        )

    assert _revoked(kit) == [False, False]
    assert kit.unit_of_work.commits == commits_before


def test_la_nueva_debe_cumplir_las_reglas(kit: AuthKit) -> None:
    user = kit.add_user()

    with pytest.raises(PasswordLengthError):
        kit.change_password().execute(ChangePasswordInput(user.id, PASSWORD, "corta"))
