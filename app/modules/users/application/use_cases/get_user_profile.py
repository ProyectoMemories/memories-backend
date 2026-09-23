"""Caso de uso: consultar el perfil de un usuario."""

import uuid

from app.modules.users.domain.entities.user import User
from app.modules.users.domain.errors import UserNotFoundError
from app.modules.users.domain.repositories.user_repository import UserRepository


class GetUserProfile:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def execute(self, user_id: uuid.UUID) -> User:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError()
        return user
