"""Construye el servicio de hashing a partir de la configuracion.

Este es el unico archivo que hay que tocar para anadir un algoritmo nuevo.
"""

from functools import lru_cache

from app.config.settings import Settings, get_settings
from app.core.security.hashing.argon2_hasher import Argon2Hasher
from app.core.security.hashing.bcrypt_hasher import BcryptHasher
from app.core.security.hashing.port import PasswordHasher
from app.core.security.hashing.service import PasswordHashingService


def build_password_hashing_service(settings: Settings) -> PasswordHashingService:
    bcrypt_hasher = BcryptHasher(rounds=settings.BCRYPT_ROUNDS)
    argon2_hasher = Argon2Hasher(
        time_cost=settings.ARGON2_TIME_COST,
        memory_cost=settings.ARGON2_MEMORY_COST,
        parallelism=settings.ARGON2_PARALLELISM,
    )
    known: list[PasswordHasher] = [bcrypt_hasher, argon2_hasher]
    es_bcrypt = settings.PASSWORD_HASHING_SCHEME == "bcrypt"  # noqa: S105 - es un algoritmo
    primary = bcrypt_hasher if es_bcrypt else argon2_hasher
    return PasswordHashingService(primary=primary, known=known)


@lru_cache(maxsize=1)
def get_password_hashing_service() -> PasswordHashingService:
    return build_password_hashing_service(get_settings())
