"""SqlUserGateway contra PostgreSQL real."""

from collections.abc import Iterator
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.modules.auth.adapters.gateways.user_gateway import SqlUserGateway
from app.modules.auth.entities.errors import EmailTakenError, UsernameTakenError
from app.modules.auth.entities.privacy_consent import PrivacyConsent
from app.modules.auth.entities.user import AccountStatus, User

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)


@pytest.fixture
def session(migrated_db: str, database_url: str) -> Iterator[Session]:
    """Una sesión cuyos cambios se descartan al terminar."""
    engine = create_engine(database_url)
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
            yield db
        transaction.rollback()
    engine.dispose()


def _user(username: str = "ana.rios", email: str = "ana@correo.com") -> User:
    return User.register(
        username=username,
        email=email,
        password_hash="hash",
        first_name="Ana",
        paternal_surname="Ríos",
        maternal_surname=None,
        birth_date=date(2000, 5, 17),
    )


def _add(gateway: SqlUserGateway, user: User) -> None:
    consent = PrivacyConsent.accept(user_id=user.id, policy_version="v1", now=NOW)
    gateway.add(user, consent)


def test_guarda_y_lee_la_entidad_completa(session: Session) -> None:
    gateway = SqlUserGateway(session)
    user = _user()
    _add(gateway, user)

    saved = gateway.get(user.id)
    assert saved is not None
    # password_changed_at lo pone la base al crear la cuenta (DEFAULT now()).
    assert saved.password_changed_at is not None
    user.password_changed_at = saved.password_changed_at
    assert saved == user
    assert gateway.get_by_email("ANA@correo.com") == user
    assert gateway.get_by_login("Ana.Rios") == user
    assert gateway.get_by_login("ana@CORREO.com") == user


def test_save_guarda_solo_lo_que_cambia_el_negocio(session: Session) -> None:
    gateway = SqlUserGateway(session)
    user = _user()
    _add(gateway, user)

    user.verify_email(NOW)
    gateway.save(user)
    session.flush()
    session.expire_all()

    saved = gateway.get(user.id)
    assert saved is not None
    assert (saved.status, saved.email_verified_at) == (AccountStatus.ACTIVE, NOW)


def test_save_guarda_el_cambio_de_contrasena(session: Session) -> None:
    gateway = SqlUserGateway(session)
    user = _user()
    _add(gateway, user)

    user.change_password("hash-nuevo", NOW)
    gateway.save(user)
    session.flush()
    session.expire_all()

    saved = gateway.get(user.id)
    assert saved is not None
    assert (saved.password_hash, saved.password_changed_at) == ("hash-nuevo", NOW)


@pytest.mark.parametrize(
    ("username", "email", "error"),
    [
        ("ANA.RIOS", "otra@correo.com", UsernameTakenError),
        ("otra.persona", "Ana@Correo.com", EmailTakenError),
    ],
)
def test_valores_repetidos_dan_el_error_de_negocio(
    session: Session, username: str, email: str, error: type
) -> None:
    gateway = SqlUserGateway(session)
    _add(gateway, _user())

    with pytest.raises(error):
        _add(gateway, _user(username, email))
