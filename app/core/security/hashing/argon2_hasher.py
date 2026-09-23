"""Implementacion con Argon2id."""

from argon2 import PasswordHasher as Argon2Backend
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


class Argon2Hasher:
    scheme = "argon2"

    def __init__(self, time_cost: int = 3, memory_cost: int = 65536, parallelism: int = 4) -> None:
        self._backend = Argon2Backend(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
        )

    def identifies(self, hashed: str) -> bool:
        return hashed.startswith("$argon2")

    def hash(self, plain: str) -> str:
        return self._backend.hash(plain)

    def verify(self, plain: str, hashed: str) -> bool:
        try:
            return self._backend.verify(hashed, plain)
        except (VerifyMismatchError, VerificationError, InvalidHashError):
            return False

    def needs_rehash(self, hashed: str) -> bool:
        try:
            return self._backend.check_needs_rehash(hashed)
        except InvalidHashError:
            return True
