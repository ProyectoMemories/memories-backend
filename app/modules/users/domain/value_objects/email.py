"""Correo electronico como objeto de valor.

Se normaliza siempre (sin espacios, en minusculas) para que dos personas no
puedan registrar "Ana@X.com" y "ana@x.com" como cuentas distintas.
"""

import re
from dataclasses import dataclass

from app.modules.users.domain.errors import InvalidEmailError

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$")
MAX_EMAIL_LENGTH = 254


@dataclass(frozen=True, slots=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not normalized:
            raise InvalidEmailError("El correo es obligatorio.")
        if len(normalized) > MAX_EMAIL_LENGTH:
            raise InvalidEmailError("El correo es demasiado largo.")
        if not EMAIL_PATTERN.match(normalized):
            raise InvalidEmailError("El correo no tiene un formato valido.")
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
