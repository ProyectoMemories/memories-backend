"""Restricciones clave del modelo físico v1.4.

Cada prueba confirma que la base rechaza un dato inválido con la restricción
exacta del modelo, o que un borrado hace lo que dicen las reglas de negocio.
"""

import uuid

import psycopg
import pytest

from tests.db.conftest import (
    assert_violates,
    new_album,
    new_memory,
    new_photo,
    new_user,
)

# ─── Cuentas ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize("username", ["joey.flores", "ana_rios", "Luis2026"])
def test_acepta_nombres_de_usuario_validos(
    conn: psycopg.Connection, username: str
) -> None:
    new_user(conn, username)


@pytest.mark.parametrize(
    "username", [".joey", "joey.", "jo..ey", "jo", "joé", "x" * 31, "con espacio"]
)
def test_rechaza_nombres_de_usuario_invalidos(
    conn: psycopg.Connection, username: str
) -> None:
    # RN-10, D40
    with pytest.raises(psycopg.errors.CheckViolation) as error, conn.transaction():
        new_user(conn, username)
    assert error.value.diag.constraint_name == "ck_app_user_username_format"


def test_usuario_y_correo_unicos_sin_importar_mayusculas(
    conn: psycopg.Connection,
) -> None:
    # RN-09
    new_user(conn, "joey", "joey@correo.com")
    with pytest.raises(psycopg.errors.UniqueViolation) as error, conn.transaction():
        new_user(conn, "JOEY")
    assert error.value.diag.constraint_name == "uq_app_user_username_ci"

    user_id = new_user(conn, "ana")
    assert_violates(
        conn,
        "uq_app_user_email_ci",
        "UPDATE app_user SET email = 'JOEY@correo.com' WHERE id = %s",
        (user_id,),
    )


def test_cuenta_suspendida_exige_fecha_de_suspension(
    conn: psycopg.Connection,
) -> None:
    # RN-16, RN-17
    user_id = new_user(conn)
    assert_violates(
        conn,
        "ck_app_user_suspended",
        "UPDATE app_user SET status = 'suspended', email_verified_at = now() "
        "WHERE id = %s",
        (user_id,),
    )


def test_updated_at_se_actualiza_solo(conn: psycopg.Connection) -> None:
    user_id = new_user(conn)
    conn.execute(
        "UPDATE app_user SET updated_at = '2000-01-01' WHERE id = %s", (user_id,)
    )
    (updated_at,) = conn.execute(
        "SELECT updated_at FROM app_user WHERE id = %s", (user_id,)
    ).fetchone()

    # El trigger reemplaza cualquier valor por now() en cada UPDATE.
    assert updated_at.year > 2000


# ─── Sesiones (D56) ───────────────────────────────────────────────────────


def test_sesion_hash_unico_y_vencimiento_posterior(conn: psycopg.Connection) -> None:
    user_id = new_user(conn)
    insert = (
        "INSERT INTO user_session (id, user_id, refresh_token_hash, platform, "
        "expires_at) VALUES (%s, %s, %s, 'web', %s)"
    )
    conn.execute(insert, (uuid.uuid4(), user_id, "hash-1", "2099-01-01"))

    assert_violates(
        conn,
        "uq_user_session_refresh_token",
        insert,
        (uuid.uuid4(), user_id, "hash-1", "2099-01-01"),
    )
    assert_violates(
        conn,
        "ck_user_session_expiry",
        insert,
        (uuid.uuid4(), user_id, "hash-2", "2000-01-01"),
    )


# ─── Álbum ────────────────────────────────────────────────────────────────


def test_album_tiene_exactamente_una_categoria(conn: psycopg.Connection) -> None:
    # RN-63, D35
    owner_id = new_user(conn)
    insert = (
        "INSERT INTO album (id, owner_id, name, base_category, custom_category) "
        "VALUES (%s, %s, %s, %s, %s)"
    )
    assert_violates(
        conn,
        "ck_album_one_category",
        insert,
        (uuid.uuid4(), owner_id, "Sin categoría", None, None),
    )
    assert_violates(
        conn,
        "ck_album_one_category",
        insert,
        (uuid.uuid4(), owner_id, "Dos categorías", "travel", "Mi viaje"),
    )


def test_nombre_de_album_unico_por_dueno(conn: psycopg.Connection) -> None:
    # RN-21
    owner_id = new_user(conn)
    other_owner_id = new_user(conn)
    new_album(conn, owner_id, "Viaje de promoción")

    with pytest.raises(psycopg.errors.UniqueViolation) as error, conn.transaction():
        new_album(conn, owner_id, "VIAJE DE PROMOCIÓN")
    assert error.value.diag.constraint_name == "uq_album_owner_name_ci"

    new_album(conn, other_owner_id, "Viaje de promoción")  # otro dueño: sí puede


def test_portada_debe_ser_foto_del_mismo_album(conn: psycopg.Connection) -> None:
    # RN-23, D29
    owner_id = new_user(conn)
    album_id = new_album(conn, owner_id)
    other_album_id = new_album(conn, owner_id)
    foreign_photo_id = new_photo(conn, other_album_id, owner_id)

    assert_violates(
        conn,
        "fk_album_cover_photo",
        "UPDATE album SET cover_photo_id = %s WHERE id = %s",
        (foreign_photo_id, album_id),
    )


# ─── Fotos (RN-37 a RN-39, RN-55) ─────────────────────────────────────────


@pytest.mark.parametrize(
    ("column", "value", "constraint"),
    [
        ("size_bytes", 5_242_881, "ck_photo_size"),
        ("mime_type", "image/gif", "ck_photo_mime_type"),
        ("latitude", -12.0464, "ck_photo_coordinates_pair"),
    ],
)
def test_rechaza_fotos_invalidas(
    conn: psycopg.Connection, column: str, value: object, constraint: str
) -> None:
    owner_id = new_user(conn)
    photo_id = new_photo(conn, new_album(conn, owner_id), owner_id)
    assert_violates(
        conn,
        constraint,
        f"UPDATE photo SET {column} = %s WHERE id = %s",  # noqa: S608
        (value, photo_id),
    )


def test_borrar_foto_respeta_las_reglas(conn: psycopg.Connection) -> None:
    owner_id = new_user(conn)
    album_id = new_album(conn, owner_id)
    photo_id = new_photo(conn, album_id, owner_id)
    description_id = uuid.uuid4()
    conn.execute(
        "INSERT INTO description (id, album_id, photo_id, written_by, text) "
        "VALUES (%s, %s, %s, %s, 'Llegamos justo para el amanecer.')",
        (description_id, album_id, photo_id, owner_id),
    )
    conn.execute(
        "UPDATE album SET cover_photo_id = %s WHERE id = %s", (photo_id, album_id)
    )
    memory_id = new_memory(conn, album_id, owner_id)
    conn.execute(
        "INSERT INTO memory_item (id, memory_id, album_id, position, item_kind, "
        "photo_id) VALUES (%s, %s, %s, 1, 'photo', %s)",
        (uuid.uuid4(), memory_id, album_id, photo_id),
    )

    conn.execute("DELETE FROM photo WHERE id = %s", (photo_id,))

    # RN-64: su descripción ligada se borra con ella.
    assert not conn.execute(
        "SELECT 1 FROM description WHERE id = %s", (description_id,)
    ).fetchone()
    # RN-24: el álbum se queda sin portada.
    assert conn.execute(
        "SELECT cover_photo_id FROM album WHERE id = %s", (album_id,)
    ).fetchone() == (None,)
    # RN-58: el recuerdo y su elemento siguen; solo pierden la referencia.
    assert conn.execute(
        "SELECT photo_id FROM memory_item WHERE memory_id = %s", (memory_id,)
    ).fetchall() == [(None,)]


# ─── Recuerdo (D37, RN-56) ────────────────────────────────────────────────


def test_elementos_del_recuerdo(conn: psycopg.Connection) -> None:
    owner_id = new_user(conn)
    album_id = new_album(conn, owner_id)
    photo_id = new_photo(conn, album_id, owner_id)
    foreign_photo_id = new_photo(conn, new_album(conn, owner_id), owner_id)
    memory_id = new_memory(conn, album_id, owner_id)
    insert = (
        "INSERT INTO memory_item (id, memory_id, album_id, position, item_kind, "
        "photo_id, description_id) VALUES (%s, %s, %s, %s, %s, %s, %s)"
    )
    conn.execute(
        insert, (uuid.uuid4(), memory_id, album_id, 1, "photo", photo_id, None)
    )

    # Dos elementos no pueden ocupar la misma posición.
    assert_violates(
        conn,
        "uq_memory_item_position",
        insert,
        (uuid.uuid4(), memory_id, album_id, 1, "photo", photo_id, None),
    )
    # Una foto de otro álbum no puede entrar al recuerdo (D32).
    assert_violates(
        conn,
        "fk_memory_item_photo",
        insert,
        (uuid.uuid4(), memory_id, album_id, 2, "photo", foreign_photo_id, None),
    )
    # Un elemento de tipo "photo" no lleva descripción.
    assert_violates(
        conn,
        "ck_memory_item_kind_photo",
        insert,
        (uuid.uuid4(), memory_id, album_id, 3, "photo", photo_id, uuid.uuid4()),
    )


def test_un_solo_enlace_activo_por_recuerdo(conn: psycopg.Connection) -> None:
    # RN-46
    owner_id = new_user(conn)
    album_id = new_album(conn, owner_id)
    memory_id = new_memory(conn, album_id, owner_id)
    insert = (
        "INSERT INTO memory_link (id, memory_id, token_hash, created_by, expires_at) "
        "VALUES (%s, %s, %s, %s, now() + interval '7 days')"
    )
    first_link_id = uuid.uuid4()
    conn.execute(insert, (first_link_id, memory_id, "token-1", owner_id))

    assert_violates(
        conn,
        "uq_memory_link_active",
        insert,
        (uuid.uuid4(), memory_id, "token-2", owner_id),
    )

    # Al anular el primero, se puede crear uno nuevo.
    conn.execute(
        "UPDATE memory_link SET revoked_at = now() WHERE id = %s", (first_link_id,)
    )
    conn.execute(insert, (uuid.uuid4(), memory_id, "token-2", owner_id))


# ─── Borrar una cuenta (RN-14, RN-15) ─────────────────────────────────────


def test_borrar_cuenta_borra_sus_albumes_y_conserva_lo_subido_a_otros(
    conn: psycopg.Connection,
) -> None:
    user_id = new_user(conn)
    other_owner_id = new_user(conn)
    own_album_id = new_album(conn, user_id)
    other_album_id = new_album(conn, other_owner_id)
    photo_in_other_album = new_photo(conn, other_album_id, user_id)

    conn.execute("DELETE FROM app_user WHERE id = %s", (user_id,))

    assert not conn.execute(
        "SELECT 1 FROM album WHERE id = %s", (own_album_id,)
    ).fetchone()
    assert conn.execute(
        "SELECT uploaded_by FROM photo WHERE id = %s", (photo_in_other_album,)
    ).fetchone() == (None,)
