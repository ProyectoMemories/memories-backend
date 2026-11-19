import pytest

from app.modules.auth.entities.user import AccountStatus
from tests.modules.auth.use_cases.conftest import AuthKit


def test_reenvia_si_la_cuenta_no_esta_verificada(kit: AuthKit) -> None:
    kit.add_user(AccountStatus.UNVERIFIED)

    kit.resend_verification().execute("ANA.RIOS@correo.com")

    [email] = kit.outbox.sent
    assert email.to == "ana.rios@correo.com"


@pytest.mark.parametrize("email", ["ana.rios@correo.com", "nadie@correo.com"])
def test_no_envia_nada_si_no_hace_falta(kit: AuthKit, email: str) -> None:
    kit.add_user(AccountStatus.ACTIVE)

    kit.resend_verification().execute(email)

    assert kit.outbox.sent == []
