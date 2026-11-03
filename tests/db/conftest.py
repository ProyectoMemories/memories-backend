"""Pruebas contra un PostgreSQL real (CLAUDE.md §11).

Usan una base aparte, cuyo nombre debe terminar en `_test`: se borra y se crea
de nuevo en cada corrida, así que nunca tocan tus datos de desarrollo.
"""

import os
import uuid
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from psycopg import sql
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]


class _TestDatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    test_database_url: str | None = None


def _alembic_config(url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    config.attributes["configure_logger"] = False
    return config


def _libpq_url(url: str) -> str:
    """psycopg no entiende el prefijo `postgresql+psycopg://` de SQLAlchemy."""
    return (
        make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)
    )


@pytest.fixture(scope="session")
def database_url() -> str:
    url = _TestDatabaseSettings().test_database_url
    if not url:
        if os.environ.get("CI"):
            pytest.fail("En el CI falta TEST_DATABASE_URL")
        pytest.skip(
            "Falta TEST_DATABASE_URL en tu .env. Levanta la base con "
            "`docker compose up -d db` (ver README)."
        )

    name = make_url(url).database or ""
    if not name.endswith("_test"):
        pytest.fail(f"La base de pruebas debe terminar en '_test' (es '{name}')")

    # Se recrea la base desde cero conectándose a la base 'postgres'.
    admin_url = _libpq_url(
        make_url(url).set(database="postgres").render_as_string(hide_password=False)
    )
    try:
        with psycopg.connect(admin_url, autocommit=True) as admin:
            admin.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                    sql.Identifier(name)
                )
            )
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    except psycopg.OperationalError as error:
        if os.environ.get("CI"):
            raise
        pytest.skip(f"No se pudo conectar a PostgreSQL: {error}")
    return url


@pytest.fixture(scope="session")
def alembic_config(database_url: str) -> Config:
    return _alembic_config(database_url)


@pytest.fixture(scope="session")
def migrated_db(database_url: str, alembic_config: Config) -> str:
    command.upgrade(alembic_config, "head")
    return _libpq_url(database_url)


@pytest.fixture
def conn(migrated_db: str) -> Iterator[psycopg.Connection]:
    """Conexión dentro de una transacción que se deshace al terminar la prueba."""
    with psycopg.connect(migrated_db) as connection:
        yield connection
        connection.rollback()


def assert_violates(
    conn: psycopg.Connection, constraint: str, query: str, params: tuple = ()
) -> None:
    """La sentencia debe fallar por esa restricción exacta, y no por otra."""
    # conn.transaction() abre un savepoint: la prueba sigue después del error.
    with pytest.raises(psycopg.errors.IntegrityError) as error, conn.transaction():
        conn.execute(query, params)
    assert error.value.diag.constraint_name == constraint


# ─── Datos mínimos para las pruebas ────────────────────────────────────────


def new_user(
    conn: psycopg.Connection, username: str | None = None, email: str | None = None
) -> uuid.UUID:
    user_id = uuid.uuid4()
    username = username or f"user_{user_id.hex[:8]}"
    email = email or f"{user_id.hex}@correo.com"
    conn.execute(
        """
        INSERT INTO app_user (id, username, email, password_hash, first_name,
                              paternal_surname, birth_date)
        VALUES (%s, %s, %s, 'hash', 'Ana', 'Ríos', '2000-01-01')
        """,
        (user_id, username, email),
    )
    return user_id


def new_album(
    conn: psycopg.Connection, owner_id: uuid.UUID, name: str | None = None
) -> uuid.UUID:
    album_id = uuid.uuid4()
    conn.execute(
        "INSERT INTO album (id, owner_id, name, base_category) "
        "VALUES (%s, %s, %s, 'travel')",
        (album_id, owner_id, name or f"Álbum {album_id.hex[:6]}"),
    )
    return album_id


def new_photo(
    conn: psycopg.Connection, album_id: uuid.UUID, uploaded_by: uuid.UUID
) -> uuid.UUID:
    photo_id = uuid.uuid4()
    conn.execute(
        """
        INSERT INTO photo (id, album_id, uploaded_by, file_key, thumbnail_key,
                           mime_type, size_bytes, width_px, height_px, taken_on)
        VALUES (%s, %s, %s, %s, %s, 'image/jpeg', 1000, 800, 600, '2026-03-01')
        """,
        (photo_id, album_id, uploaded_by, f"p/{photo_id}", f"t/{photo_id}"),
    )
    return photo_id


def new_memory(
    conn: psycopg.Connection, album_id: uuid.UUID, creator_id: uuid.UUID
) -> uuid.UUID:
    memory_id = uuid.uuid4()
    conn.execute(
        "INSERT INTO memory (id, album_id, creator_id, title, output_type) "
        "VALUES (%s, %s, %s, 'Amanecer', 'collage')",
        (memory_id, album_id, creator_id),
    )
    return memory_id
