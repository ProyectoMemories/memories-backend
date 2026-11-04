"""Contraseñas: hash con pwdlib y Argon2 (D62-D) y reglas de D62-B."""

from functools import lru_cache
from pathlib import Path

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

MIN_LENGTH = 8
MAX_LENGTH = 64
_COMMON_PASSWORDS_FILE = Path(__file__).with_name("common_passwords.txt")


class PasswordHasher:
    """Interfaz pequeña para poder cambiar el algoritmo sin tocar el servicio (RNF-08).

    pwdlib reconoce los hashes de cada algoritmo registrado; para migrar se agrega
    el nuevo hasher al principio de la tupla y los hashes viejos se recalculan al
    iniciar sesión.
    """

    def __init__(self, hasher: Argon2Hasher | None = None) -> None:
        self._password_hash = PasswordHash((hasher or Argon2Hasher(),))
        self._dummy_hash: str | None = None

    def hash(self, password: str) -> str:
        return self._password_hash.hash(password)

    def verify_and_update(
        self, password: str, password_hash: str
    ) -> tuple[bool, str | None]:
        """Devuelve si coincide y, si el hash usa parámetros viejos, uno nuevo."""
        return self._password_hash.verify_and_update(password, password_hash)

    def verify_dummy(self, password: str) -> None:
        """Gasta lo mismo que una verificación real cuando la cuenta no existe.

        Así el tiempo de respuesta del login no revela qué cuentas existen.
        """
        if self._dummy_hash is None:
            self._dummy_hash = self.hash("cuenta-que-no-existe")
        self._password_hash.verify(password, self._dummy_hash)


@lru_cache
def _common_passwords() -> frozenset[str]:
    lines = _COMMON_PASSWORDS_FILE.read_text(encoding="utf-8").splitlines()
    return frozenset(line for line in lines if line and not line.startswith("#"))


def password_problem(password: str) -> str | None:
    """Qué incumple la contraseña según D62-B, o None si sirve."""
    if not MIN_LENGTH <= len(password) <= MAX_LENGTH:
        return "length"
    # Sin reglas de composición: largo y que no sea común, como pide NIST.
    if password.lower() in _common_passwords():
        return "common"
    return None
