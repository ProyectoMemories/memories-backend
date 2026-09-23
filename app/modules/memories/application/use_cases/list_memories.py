"""Caso de uso: listar los recuerdos propios (capacidad CP-03)."""

import uuid
from dataclasses import dataclass
from datetime import date

from app.modules.memories.domain.entities.memory import Memory
from app.modules.memories.domain.repositories.memory_repository import MemoryRepository
from app.shared.pagination import Page, PageRequest


@dataclass(frozen=True, slots=True)
class ListMemoriesQuery:
    owner_id: uuid.UUID
    page: PageRequest
    date_from: date | None = None
    date_to: date | None = None
    search: str | None = None


class ListMemories:
    def __init__(self, memories: MemoryRepository) -> None:
        self._memories = memories

    async def execute(self, query: ListMemoriesQuery) -> Page[Memory]:
        items, total = await self._memories.list_for_owner(
            query.owner_id,
            offset=query.page.offset,
            limit=query.page.size,
            date_from=query.date_from,
            date_to=query.date_to,
            search=query.search,
        )
        return Page(items=items, total=total, page=query.page.page, size=query.page.size)
