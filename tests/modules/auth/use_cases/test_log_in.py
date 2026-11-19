from datetime import timedelta

import pytest

from app.modules.auth.entities.errors import EmailNotVerifiedError
from app.modules.auth.entities.user import AccountStatus
from app.modules.auth.entities.user_session import ClientPlatform
from app.modules.auth.use_cases.errors import InvalidCredentialsError
from app.modules.auth.use_cases.log_in import LogInInput
from tests.modules.auth.use_cases.conftest import PASSWORD, AuthKit


def _input(identifier: str = "ana.rios", password: str = PASSWORD) -> LogInInput:
    return LogInInput(
        identifier=identifier,
        password=password,
        platform=ClientPlatform.ANDROID,
        device_name="Pixel 8",
    )


def test_abre_una_sesion_y_entrega_los_tokens(kit: AuthKit) -> None:
    user = kit.add_user()

    issued = kit.log_in().execute(_input("ANA.RIOS@correo.com"))

    [user_session] = kit.sessions.sessions.values()
    assert user_session.user_id == user.id
    assert user_session.refresh_token_hash == kit.secrets.hash("secret-1")
    assert issued.refresh_token == f"{user_session.id}.secret-1"
    assert issued.expires_in == 15 * 60
    assert kit.unit_of_work.commits == 1


def test_usuario_inexistente_gasta_un_hash_y_da_el_error_generico(kit: AuthKit) -> None:
    with pytest.raises(InvalidCredentialsError):
        kit.log_in().execute(_input("nadie"))
    assert kit.hasher.dummy_checks == 1


def test_contrasena_incorrecta(kit: AuthKit) -> None:
    kit.add_user()

    with pytest.raises(InvalidCredentialsError):
        kit.log_in().execute(_input(password="otra cosa"))
    assert kit.sessions.sessions == {}


def test_sin_verificar_con_la_contrasena_correcta(kit: AuthKit) -> None:
    kit.add_user(AccountStatus.UNVERIFIED)

    with pytest.raises(EmailNotVerifiedError):
        kit.log_in().execute(_input())
    assert kit.unit_of_work.commits == 0


def test_eliminacion_vencida_responde_como_cuenta_inexistente(kit: AuthKit) -> None:
    user = kit.add_user(AccountStatus.PENDING_DELETION)
    user.deletion_requested_at = kit.clock() - timedelta(days=30)
    kit.users.save(user)

    with pytest.raises(InvalidCredentialsError):
        kit.log_in().execute(_input())


def test_actualiza_un_hash_con_parametros_viejos(kit: AuthKit) -> None:
    user = kit.add_user()
    user.password_hash = f"old:{PASSWORD}"
    kit.users.save(user)

    kit.log_in().execute(_input())

    assert kit.users.get(user.id).password_hash == kit.hasher.hash(PASSWORD)  # type: ignore[union-attr]
