import uuid
from datetime import timedelta

import pytest

from app.modules.auth.entities.user import AccountStatus
from app.modules.auth.entities.user_session import ClientPlatform
from app.modules.auth.use_cases.errors import (
    AccessTokenExpiredError,
    NotAuthenticatedError,
)
from app.modules.auth.use_cases.log_in import LogInInput
from app.modules.auth.use_cases.log_out import LogOutInput
from app.modules.auth.use_cases.token_issuer import IssuedTokens
from tests.modules.auth.use_cases.conftest import PASSWORD, AuthKit

ANDROID = ClientPlatform.ANDROID


def _log_in(kit: AuthKit) -> IssuedTokens:
    return kit.log_in().execute(LogInInput("ana.rios", PASSWORD, ANDROID, None))


def test_devuelve_el_usuario_del_token(kit: AuthKit) -> None:
    user = kit.add_user()

    current = kit.authenticate().execute(_log_in(kit).access_token)

    assert (current.id, current.username) == (user.id, "ana.rios")


def test_token_vencido_pide_renovar(kit: AuthKit) -> None:
    kit.add_user()
    access = _log_in(kit).access_token
    kit.clock.advance(timedelta(minutes=15))

    with pytest.raises(AccessTokenExpiredError):
        kit.authenticate().execute(access)


def test_tras_cerrar_sesion_el_token_deja_de_servir(kit: AuthKit) -> None:
    kit.add_user()
    issued = _log_in(kit)
    kit.log_out().execute(LogOutInput(issued.refresh_token, ANDROID))

    with pytest.raises(NotAuthenticatedError) as caught:
        kit.authenticate().execute(issued.access_token)
    assert type(caught.value) is NotAuthenticatedError


def test_token_que_mezcla_usuario_y_sesion_ajena(kit: AuthKit) -> None:
    kit.add_user()
    issued = _log_in(kit)
    session_id = issued.refresh_token.split(".")[0]
    forged = kit.access_tokens.create(
        uuid.uuid4(), uuid.UUID(session_id), timedelta(minutes=15), kit.clock()
    )

    with pytest.raises(NotAuthenticatedError):
        kit.authenticate().execute(forged)


def test_cuenta_suspendida_con_token_vigente(kit: AuthKit) -> None:
    user = kit.add_user()
    access = _log_in(kit).access_token
    user.status = AccountStatus.SUSPENDED
    kit.users.save(user)

    with pytest.raises(NotAuthenticatedError):
        kit.authenticate().execute(access)


def test_token_que_no_es_de_acceso(kit: AuthKit) -> None:
    with pytest.raises(NotAuthenticatedError):
        kit.authenticate().execute("verify_email|x|y")
