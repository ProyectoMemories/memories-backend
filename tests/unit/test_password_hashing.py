"""El algoritmo de hashing se puede cambiar sin invalidar contrasenas (RNF-08)."""

import pytest

from app.core.security.hashing.argon2_hasher import Argon2Hasher
from app.core.security.hashing.bcrypt_hasher import BcryptHasher
from app.core.security.hashing.service import PasswordHashingService

CLAVE = "unaClaveSegura1"


def servicio(primario: str) -> PasswordHashingService:
    bcrypt_hasher = BcryptHasher(rounds=4)
    argon2_hasher = Argon2Hasher(time_cost=1, memory_cost=8, parallelism=1)
    principal = bcrypt_hasher if primario == "bcrypt" else argon2_hasher
    return PasswordHashingService(primary=principal, known=[bcrypt_hasher, argon2_hasher])


@pytest.mark.parametrize("esquema", ["bcrypt", "argon2"])
def test_una_contrasena_se_verifica_contra_su_propio_hash(esquema: str) -> None:
    hashing = servicio(esquema)
    hashed = hashing.hash(CLAVE)

    assert hashing.verify(CLAVE, hashed)
    assert not hashing.verify("otraClaveDistinta1", hashed)


def test_dos_hashes_de_la_misma_clave_son_distintos() -> None:
    hashing = servicio("bcrypt")
    assert hashing.hash(CLAVE) != hashing.hash(CLAVE)


def test_al_cambiar_de_algoritmo_las_contrasenas_antiguas_siguen_valiendo() -> None:
    hash_antiguo = servicio("bcrypt").hash(CLAVE)
    nuevo = servicio("argon2")

    assert nuevo.verify(CLAVE, hash_antiguo)
    # Y se marca para volver a hashearla en el siguiente inicio de sesion.
    assert nuevo.needs_rehash(hash_antiguo)


def test_un_hash_del_algoritmo_vigente_no_necesita_rehash() -> None:
    hashing = servicio("argon2")
    assert not hashing.needs_rehash(hashing.hash(CLAVE))


def test_un_hash_con_formato_desconocido_no_verifica() -> None:
    hashing = servicio("bcrypt")
    assert not hashing.verify(CLAVE, "esto-no-es-un-hash")
    assert hashing.needs_rehash("esto-no-es-un-hash")
