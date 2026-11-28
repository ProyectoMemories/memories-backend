"""Entidad Profile: los datos con que una persona se reconoce en la app (RF-04).

No lleva la fecha de nacimiento, la contraseña ni el estado de la cuenta: la
app no los necesita para mostrar quién inició sesión (privacidad por defecto).
"""

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    id: uuid.UUID
    username: str
    email: str
    first_name: str
    paternal_surname: str
    maternal_surname: str | None
