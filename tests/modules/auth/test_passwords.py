import pytest
from pwdlib.hashers.argon2 import Argon2Hasher

from app.modules.auth.passwords import PasswordHasher, password_problem


def test_el_hash_verifica_la_contrasena_correcta() -> None:
    hasher = PasswordHasher()
    password_hash = hasher.hash("caballo bateria grapa")

    assert password_hash.startswith("$argon2id$")
    assert hasher.verify_and_update("caballo bateria grapa", password_hash) == (
        True,
        None,
    )


def test_el_hash_rechaza_otra_contrasena() -> None:
    hasher = PasswordHasher()
    password_hash = hasher.hash("caballo bateria grapa")

    valid, _ = hasher.verify_and_update("otra contraseña", password_hash)

    assert not valid


def test_recalcula_hashes_con_parametros_viejos() -> None:
    old_hash = PasswordHasher(Argon2Hasher(time_cost=1)).hash("caballo bateria grapa")

    valid, new_hash = PasswordHasher().verify_and_update(
        "caballo bateria grapa", old_hash
    )

    assert valid
    assert new_hash is not None
    assert new_hash != old_hash


@pytest.mark.parametrize(
    ("password", "problem"),
    [
        ("a" * 7 + "Z", None),  # 8: el mínimo
        ("x7Kp2mQ", "length"),  # 7
        ("q" * 64, None),  # 64: el máximo
        ("q" * 65, "length"),
        ("password", "common"),
        ("PassWord", "common"),  # sin importar mayúsculas
        ("solo letras minusculas", None),  # sin reglas de composición (D62-B)
    ],
)
def test_reglas_de_la_contrasena(password: str, problem: str | None) -> None:
    assert password_problem(password) == problem
