from pwdlib.hashers.argon2 import Argon2Hasher

from app.modules.auth.adapters.services.argon2_password_hasher import (
    Argon2PasswordHasher,
)

PASSWORD = "caballo bateria grapa"


def test_el_hash_verifica_la_contrasena_correcta() -> None:
    hasher = Argon2PasswordHasher()
    password_hash = hasher.hash(PASSWORD)

    assert password_hash.startswith("$argon2id$")
    assert hasher.verify_and_update(PASSWORD, password_hash) == (True, None)


def test_el_hash_rechaza_otra_contrasena() -> None:
    hasher = Argon2PasswordHasher()

    valid, _ = hasher.verify_and_update("otra contraseña", hasher.hash(PASSWORD))

    assert not valid


def test_recalcula_hashes_con_parametros_viejos() -> None:
    old_hash = Argon2PasswordHasher(Argon2Hasher(time_cost=1)).hash(PASSWORD)

    valid, new_hash = Argon2PasswordHasher().verify_and_update(PASSWORD, old_hash)

    assert valid
    assert new_hash is not None
    assert new_hash != old_hash


def test_verificacion_falsa_no_falla() -> None:
    Argon2PasswordHasher().verify_dummy(PASSWORD)
