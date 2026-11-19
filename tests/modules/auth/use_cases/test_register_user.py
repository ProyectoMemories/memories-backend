from datetime import date, timedelta
from urllib.parse import parse_qs, urlparse

import pytest

from app.modules.auth.entities.age_policy import UnderageError
from app.modules.auth.entities.errors import UsernameTakenError
from app.modules.auth.entities.password_policy import PasswordTooCommonError
from app.modules.auth.entities.privacy_consent import PrivacyPolicyNotAcceptedError
from app.modules.auth.entities.user import AccountStatus
from app.modules.auth.use_cases.register_user import RegisterUserInput
from tests.modules.auth.use_cases.conftest import PASSWORD, AuthKit


def _input(**changes: object) -> RegisterUserInput:
    data = {
        "username": "ana.rios",
        "email": "ana@correo.com",
        "password": PASSWORD,
        "first_name": "Ana",
        "paternal_surname": "Ríos",
        "maternal_surname": None,
        "birth_date": date(2000, 5, 17),
        "accepts_privacy_policy": True,
    }
    return RegisterUserInput(**{**data, **changes})  # type: ignore[arg-type]


def test_crea_la_cuenta_sin_verificar_con_su_consentimiento(kit: AuthKit) -> None:
    registered = kit.register_user().execute(_input())

    assert registered.status is AccountStatus.UNVERIFIED
    saved = kit.users.get(registered.id)
    assert saved is not None
    assert saved.password_hash == kit.hasher.hash(PASSWORD)
    [consent] = kit.users.consents
    assert (consent.user_id, consent.policy_version) == (registered.id, "2026-11")
    assert kit.unit_of_work.commits == 1


def test_envia_el_enlace_que_sirve_para_verificar(kit: AuthKit) -> None:
    registered = kit.register_user().execute(_input())

    [email] = kit.outbox.sent
    link = next(word for word in email.text.split() if "/verify-email?" in word)
    assert link.startswith("http://localhost:3000/verify-email?")
    [token] = parse_qs(urlparse(link).query)["token"]
    kit.verify_email().execute(token)
    assert kit.users.get(registered.id).status is AccountStatus.ACTIVE  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"accepts_privacy_policy": False}, PrivacyPolicyNotAcceptedError),
        ({"password": "Password"}, PasswordTooCommonError),
    ],
)
def test_reglas_que_impiden_registrarse(
    kit: AuthKit, changes: dict, error: type
) -> None:
    with pytest.raises(error):
        kit.register_user().execute(_input(**changes))
    assert kit.users.users == {}
    assert kit.outbox.sent == []


def test_menor_de_14_no_se_registra(kit: AuthKit) -> None:
    today = kit.clock().date()
    birth_date = today.replace(year=today.year - 14) + timedelta(days=1)

    with pytest.raises(UnderageError):
        kit.register_user().execute(_input(birth_date=birth_date))
    assert kit.unit_of_work.commits == 0


def test_usuario_repetido_no_confirma_ni_envia_correo(kit: AuthKit) -> None:
    kit.add_user(username="ana.rios")

    with pytest.raises(UsernameTakenError):
        kit.register_user().execute(_input(email="otra@correo.com"))
    assert kit.unit_of_work.commits == 0
    assert kit.outbox.sent == []


def test_si_el_correo_falla_la_cuenta_queda(kit: AuthKit) -> None:
    kit.outbox.failing = True

    registered = kit.register_user().execute(_input())

    assert kit.users.get(registered.id) is not None
