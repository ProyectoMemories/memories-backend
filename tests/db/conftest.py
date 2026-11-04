"""Pruebas de la base: restricciones y datos mínimos.

Los fixtures que crean la base de pruebas están en tests/conftest.py.
"""

import uuid
from collections.abc import Iterator

import psycopg
import pytest


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
