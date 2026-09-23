"""Puerto del repositorio de usuarios.

Lo define el dominio y lo implementa la infraestructura: por eso los casos de
uso se pueden probar con un doble en memoria, sin Postgres.
"""

import uuid
from typing import Protocol

from app.modules.users.domain.entities.user import User
from app.modules.users.domain.value_objects.email import Email


class UserRepository(Protocol):
    async def add(self, user: User) -> None: ...

    async def update(self, user: User) -> None: ...

    async def get_by_id(self, user_id: uuid.UUID) -> User | None: ...

    async def get_by_email(self, email: Email) -> User | None: ...

    async def exists_with_email(self, email: Email) -> bool: ...

    async def list_all(self, offset: int, limit: int) -> tuple[list[User], int]:
        """Devuelve la pagina pedida y el total. Solo la usa el superusuario."""
        ...
