"""Politica de contrasenas.

Es una regla de negocio, no un detalle de infraestructura: por eso vive en el
dominio y no en el hasher. El maximo de 72 bytes existe porque bcrypt ignora
todo lo que pase de ahi (ver app/core/security/hashing/bcrypt_hasher.py).
"""

from dataclasses import dataclass

from app.modules.users.domain.errors import WeakPasswordError

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_BYTES = 72


@dataclass(frozen=True, slots=True)
class RawPassword:
    """Contrasena en claro, validada. Nunca se persiste ni se registra en logs."""

    value: str

    def __post_init__(self) -> None:
        if len(self.value) < MIN_PASSWORD_LENGTH:
            raise WeakPasswordError(
                f"La contrasena debe tener al menos {MIN_PASSWORD_LENGTH} caracteres."
            )
        if len(self.value.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise WeakPasswordError("La contrasena es demasiado larga.")
        if self.value.strip() != self.value:
            raise WeakPasswordError("La contrasena no puede empezar ni terminar con espacios.")

    def __str__(self) -> str:  # pragma: no cover - evita filtrarla por accidente
        return "********"

    def __repr__(self) -> str:  # pragma: no cover
        return "RawPassword(********)"
