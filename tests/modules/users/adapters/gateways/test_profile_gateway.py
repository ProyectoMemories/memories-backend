"""SqlProfileGateway contra PostgreSQL real."""

import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.modules.users.adapters.gateways.profile_gateway import SqlProfileGateway
from app.modules.users.entities.profile import Profile


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


def _insert_user(
    session: Session, username: str, maternal_surname: str | None
) -> uuid.UUID:
    # Con SQL directo: la cuenta la crea auth, y users no usa su gateway.
    user_id = uuid.uuid4()
    session.execute(
        text(
            "INSERT INTO app_user (id, username, email, password_hash, first_name,"
            " paternal_surname, maternal_surname, birth_date)"
            " VALUES (:id, :username, :email, 'hash', 'Ana', 'Ríos',"
            " :maternal_surname, '2000-05-17')"
        ),
        {
            "id": user_id,
            "username": username,
            "email": f"{username}@correo.com",
            "maternal_surname": maternal_surname,
        },
    )
    return user_id


def test_lee_las_columnas_del_perfil(session: Session) -> None:
    user_id = _insert_user(session, "ana.rios", maternal_surname="Paz")

    assert SqlProfileGateway(session).get(user_id) == Profile(
        id=user_id,
        username="ana.rios",
        email="ana.rios@correo.com",
        first_name="Ana",
        paternal_surname="Ríos",
        maternal_surname="Paz",
    )


def test_apellido_materno_vacio_es_none(session: Session) -> None:
    user_id = _insert_user(session, "ana.rios", maternal_surname=None)

    profile = SqlProfileGateway(session).get(user_id)

    assert profile is not None
    assert profile.maternal_surname is None


def test_cuenta_que_no_existe_devuelve_none(session: Session) -> None:
    assert SqlProfileGateway(session).get(uuid.uuid4()) is None
