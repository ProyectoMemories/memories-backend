"""Implementacion con bcrypt."""

import bcrypt

# bcrypt ignora todo lo que pase de 72 bytes. En vez de truncar en silencio
# (dos contrasenas distintas acabarian valiendo lo mismo) se rechaza antes.
BCRYPT_MAX_BYTES = 72


class BcryptHasher:
    scheme = "bcrypt"
    _PREFIXES = ("$2a$", "$2b$", "$2y$")

    def __init__(self, rounds: int = 12) -> None:
        self._rounds = rounds

    def identifies(self, hashed: str) -> bool:
        return hashed.startswith(self._PREFIXES)

    def hash(self, plain: str) -> str:
        encoded = self._encode(plain)
        return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=self._rounds)).decode("utf-8")

    def verify(self, plain: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(self._encode(plain), hashed.encode("utf-8"))
        except ValueError:
            # Hash con formato invalido: se trata como credencial incorrecta.
            return False

    def needs_rehash(self, hashed: str) -> bool:
        try:
            rounds = int(hashed.split("$")[2])
        except (IndexError, ValueError):
            return True
        return rounds != self._rounds

    @staticmethod
    def _encode(plain: str) -> bytes:
        encoded = plain.encode("utf-8")
        if len(encoded) > BCRYPT_MAX_BYTES:
            raise ValueError(f"bcrypt admite como maximo {BCRYPT_MAX_BYTES} bytes de contrasena.")
        return encoded
