import uuid
from datetime import timedelta

import pytest

from app.modules.auth.entities.user import AccountStatus
from app.modules.auth.use_cases.errors import ExpiredLinkError, InvalidLinkError
from app.modules.auth.use_cases.ports import TokenPurpose
from tests.modules.auth.use_cases.conftest import AuthKit


def _link(kit: AuthKit, user_id: uuid.UUID) -> str:
    return kit.email_links.create(
        user_id, TokenPurpose.VERIFY_EMAIL, timedelta(hours=24), kit.clock()
    )


def test_activa_la_cuenta_y_repetir_no_cambia_nada(kit: AuthKit) -> None:
    user = kit.add_user(AccountStatus.UNVERIFIED)
    token = _link(kit, user.id)

    kit.verify_email().execute(token)
    kit.clock.advance(timedelta(hours=1))
    kit.verify_email().execute(token)

    saved = kit.users.get(user.id)
    assert saved is not None and saved.is_active
    assert saved.email_verified_at == kit.clock() - timedelta(hours=1)
    assert kit.unit_of_work.commits == 1


def test_enlace_vencido(kit: AuthKit) -> None:
    user = kit.add_user(AccountStatus.UNVERIFIED)
    token = _link(kit, user.id)
    kit.clock.advance(timedelta(hours=24))

    with pytest.raises(ExpiredLinkError):
        kit.verify_email().execute(token)


@pytest.mark.parametrize(
    "token", ["basura", "verify_email|no-es-uuid|2099-01-01T00:00:00+00:00"]
)
def test_enlace_invalido(kit: AuthKit, token: str) -> None:
    with pytest.raises(InvalidLinkError):
        kit.verify_email().execute(token)


def test_enlace_de_una_cuenta_que_ya_no_existe(kit: AuthKit) -> None:
    with pytest.raises(InvalidLinkError):
        kit.verify_email().execute(_link(kit, uuid.uuid4()))
