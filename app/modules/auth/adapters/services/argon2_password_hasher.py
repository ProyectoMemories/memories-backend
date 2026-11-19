"""PasswordHasher con pwdlib y Argon2 (D62-D).

Para cambiar de algoritmo (RNF-08) se agrega el nuevo hasher al principio de
la tupla: pwdlib reconoce los hashes viejos y se recalculan al iniciar sesión.
"""

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher


class Argon2PasswordHasher:
    def __init__(self, hasher: Argon2Hasher | None = None) -> None:
        self._password_hash = PasswordHash((hasher or Argon2Hasher(),))
        self._dummy_hash: str | None = None

    def hash(self, password: str) -> str:
        return self._password_hash.hash(password)

    def verify_and_update(
        self, password: str, password_hash: str
    ) -> tuple[bool, str | None]:
        return self._password_hash.verify_and_update(password, password_hash)

    def verify_dummy(self, password: str) -> None:
        if self._dummy_hash is None:
            self._dummy_hash = self.hash("cuenta-que-no-existe")
        self._password_hash.verify(password, self._dummy_hash)
