"""Caso de uso: revivir recuerdos (capacidad CP-05).

La regla de que mostrar vive en el dominio (revive_selector); aqui solo se
consulta y se pasa. Cuando el equipo cierre el pendiente P15 del PRD, el cambio
se hace en el selector, no en este archivo.
"""

import uuid
from datetime import UTC, date, datetime

from app.modules.memories.domain.repositories.memory_repository import MemoryRepository
from app.modules.memories.domain.services.revive_selector import (
    ReviveSelection,
    choose_revive_memories,
)

DEFAULT_REVIVE_LIMIT = 3


class ReviveMemories:
    def __init__(self, memories: MemoryRepository, limit: int = DEFAULT_REVIVE_LIMIT) -> None:
        self._memories = memories
        self._limit = limit

    async def execute(self, owner_id: uuid.UUID, today: date | None = None) -> ReviveSelection:
        reference = today or datetime.now(tz=UTC).date()

        on_this_day = await self._memories.list_on_this_day(
            owner_id,
            reference.month,
            reference.day,
            exclude_year=reference.year,
            limit=self._limit,
        )
        fallback = [] if on_this_day else await self._memories.list_random(owner_id, self._limit)
        return choose_revive_memories(on_this_day, fallback, self._limit)
