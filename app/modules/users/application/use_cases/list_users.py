"""Caso de uso: listar usuarios (solo superusuario)."""

from app.modules.users.domain.entities.user import User
from app.modules.users.domain.repositories.user_repository import UserRepository
from app.shared.pagination import Page, PageRequest


class ListUsers:
    def __init__(self, users: UserRepository) -> None:
        self._users = users

    async def execute(self, page_request: PageRequest) -> Page[User]:
        items, total = await self._users.list_all(
            offset=page_request.offset, limit=page_request.size
        )
        return Page(items=items, total=total, page=page_request.page, size=page_request.size)
