from urllib.parse import parse_qs, urlparse

import pytest

from app.modules.auth.entities.user import AccountStatus
from tests.modules.auth.use_cases.conftest import AuthKit


def test_envia_el_enlace_a_la_app_web(kit: AuthKit) -> None:
    user = kit.add_user()

    kit.request_password_reset().execute("ANA.RIOS@correo.com")

    [email] = kit.outbox.sent
    link = next(word for word in email.text.split() if "/reset-password?" in word)
    assert link.startswith("http://localhost:3000/reset-password?")
    [token] = parse_qs(urlparse(link).query)["token"]
    assert kit.reset_tokens.read(token) == (user.id, user.password_changed_at)


@pytest.mark.parametrize(
    "status",
    [AccountStatus.ACTIVE, AccountStatus.UNVERIFIED, AccountStatus.DEACTIVATED],
)
def test_cuentas_que_pueden_recuperarse(kit: AuthKit, status: AccountStatus) -> None:
    kit.add_user(status)

    kit.request_password_reset().execute("ana.rios@correo.com")

    assert len(kit.outbox.sent) == 1


@pytest.mark.parametrize("email", ["nadie@correo.com", "ana.rios@correo.com"])
def test_no_envia_a_cuentas_inexistentes_ni_suspendidas(
    kit: AuthKit, email: str
) -> None:
    kit.add_user(AccountStatus.SUSPENDED)

    kit.request_password_reset().execute(email)

    assert kit.outbox.sent == []
