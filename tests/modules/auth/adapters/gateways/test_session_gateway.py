"""SqlSessionGateway contra PostgreSQL real."""

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.modules.auth.adapters.gateways.session_gateway import SqlSessionGateway
from app.modules.auth.adapters.gateways.user_gateway import SqlUserGateway
from app.modules.auth.entities.privacy_consent import PrivacyConsent
from app.modules.auth.entities.user import User
from app.modules.auth.entities.user_session import ClientPlatform, UserSession

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)


@pytest.fixture
def session(migrated_db: str, database_url: str) -> Iterator[Session]:
    engine = create_engine(database_url)
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
            yield db
        transaction.rollback()
    engine.dispose()


@pytest.fixture
def user(session: Session) -> User:
    user = User.register(
        username="ana.rios",
        email="ana@correo.com",
        password_hash="hash",
        first_name="Ana",
        paternal_surname="Ríos",
        maternal_surname=None,
        birth_date=date(2000, 5, 17),
    )
    consent = PrivacyConsent.accept(user_id=user.id, policy_version="v1", now=NOW)
    SqlUserGateway(session).add(user, consent)
    return user


def _open(user: User) -> UserSession:
    return UserSession.open(
        user_id=user.id,
        platform=ClientPlatform.WEB,
        device_name="Chrome",
        refresh_token_hash="hash-1",
        now=NOW,
    )


def test_guarda_y_lee_la_sesion(session: Session, user: User) -> None:
    gateway = SqlSessionGateway(session)
    user_session = _open(user)

    gateway.add(user_session)
    session.flush()

    assert gateway.get(user_session.id) == user_session
    assert gateway.get_for_update(user_session.id) == user_session


def test_save_guarda_la_rotacion_y_la_revocacion(session: Session, user: User) -> None:
    gateway = SqlSessionGateway(session)
    user_session = _open(user)
    gateway.add(user_session)
    session.flush()

    user_session.rotate("hash-2", NOW + timedelta(days=1))
    user_session.revoke(NOW + timedelta(days=2))
    gateway.save(user_session)
    session.flush()
    session.expire_all()

    assert gateway.get(user_session.id) == user_session
