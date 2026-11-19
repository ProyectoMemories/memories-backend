from datetime import UTC, date, datetime, timedelta

import pytest

from app.modules.auth.entities.errors import (
    AccountSuspendedError,
    DeletionPeriodOverError,
    EmailNotVerifiedError,
)
from app.modules.auth.entities.user import AccountStatus, User

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)


def _user(status: AccountStatus = AccountStatus.ACTIVE, **changes: object) -> User:
    user = User.register(
        username="ana.rios",
        email="ana@correo.com",
        password_hash="hash",
        first_name="Ana",
        paternal_surname="Ríos",
        maternal_surname=None,
        birth_date=date(2000, 5, 17),
    )
    user.status = status
    for field, value in changes.items():
        setattr(user, field, value)
    return user


def test_una_cuenta_nueva_empieza_sin_verificar() -> None:
    user = _user(AccountStatus.UNVERIFIED)
    fresh = User.register(
        username=user.username,
        email=user.email,
        password_hash="hash",
        first_name="Ana",
        paternal_surname="Ríos",
        maternal_surname=None,
        birth_date=user.birth_date,
    )

    assert fresh.status is AccountStatus.UNVERIFIED
    assert fresh.id.version == 7
    assert fresh.id != user.id


def test_verificar_activa_la_cuenta_una_sola_vez() -> None:
    user = _user(AccountStatus.UNVERIFIED)

    assert user.verify_email(NOW) is True
    assert (user.status, user.email_verified_at) == (AccountStatus.ACTIVE, NOW)
    assert user.verify_email(NOW + timedelta(hours=1)) is False
    assert user.email_verified_at == NOW


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (AccountStatus.UNVERIFIED, EmailNotVerifiedError),
        (AccountStatus.SUSPENDED, AccountSuspendedError),
    ],
)
def test_estados_que_no_pueden_entrar(status: AccountStatus, error: type) -> None:
    with pytest.raises(error):
        _user(status).admit_login(NOW)


def test_entrar_reactiva_una_cuenta_desactivada() -> None:
    user = _user(AccountStatus.DEACTIVATED)

    user.admit_login(NOW)

    assert user.is_active


def test_entrar_dentro_de_30_dias_cancela_la_eliminacion() -> None:
    user = _user(
        AccountStatus.PENDING_DELETION, deletion_requested_at=NOW - timedelta(days=29)
    )

    user.admit_login(NOW)

    assert (user.status, user.deletion_requested_at) == (AccountStatus.ACTIVE, None)


def test_pasados_30_dias_ya_no_se_puede_cancelar() -> None:
    user = _user(
        AccountStatus.PENDING_DELETION, deletion_requested_at=NOW - timedelta(days=30)
    )

    with pytest.raises(DeletionPeriodOverError):
        user.admit_login(NOW)
    assert user.status is AccountStatus.PENDING_DELETION


def test_cambiar_la_contrasena_mueve_la_fecha() -> None:
    user = _user()

    user.change_password("hash-nuevo", NOW)

    assert (user.password_hash, user.password_changed_at) == ("hash-nuevo", NOW)


def test_rehacer_el_hash_no_cuenta_como_cambio() -> None:
    user = _user()

    user.replace_password_hash("hash-al-dia")

    assert user.password_hash == "hash-al-dia"
    assert user.password_changed_at is None


@pytest.mark.parametrize(
    ("status", "can_recover"),
    [
        (AccountStatus.ACTIVE, True),
        (AccountStatus.UNVERIFIED, True),
        (AccountStatus.DEACTIVATED, True),
        (AccountStatus.PENDING_DELETION, True),
        (AccountStatus.SUSPENDED, False),
    ],
)
def test_quien_puede_recuperar_la_contrasena(
    status: AccountStatus, can_recover: bool
) -> None:
    assert _user(status).can_recover_password is can_recover
