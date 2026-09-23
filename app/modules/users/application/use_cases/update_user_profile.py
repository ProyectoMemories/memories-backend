"""Caso de uso: cambiar el nombre visible del propio usuario."""

import uuid

from app.modules.users.domain.entities.user import User
from app.modules.users.domain.errors import UserNotFoundError
from app.modules.users.domain.repositories.user_repository import UserRepository


class UpdateUserProfile:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def execute(self, user_id: uuid.UUID, display_name: str) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        user.rename(display_name)
        await self._users.update(user)
        return user
