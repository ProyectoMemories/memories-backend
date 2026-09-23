"""Puerto del repositorio de recuerdos.

Todas las operaciones piden owner_id: la privacidad por defecto del PRD no es
un filtro que se recuerda poner en cada consulta, es parte del contrato.
"""

import uuid
from datetime import date
from typing import Protocol

from app.modules.memories.domain.entities.memory import Memory


class MemoryRepository(Protocol):
    async def add(self, memory: Memory) -> None: ...

    async def update(self, memory: Memory) -> None: ...

    async def delete(self, memory: Memory) -> None: ...

    async def get(self, memory_id: uuid.UUID, owner_id: uuid.UUID) -> Memory | None: ...

    async def list_for_owner(
        self,
        owner_id: uuid.UUID,
        *,
        offset: int,
        limit: int,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
    ) -> tuple[list[Memory], int]: ...

    async def count_by_day(self, owner_id: uuid.UUID, year: int, month: int) -> dict[date, int]:
        """Cuantos recuerdos hay en cada dia del mes (vista calendario)."""
        ...

    async def list_on_this_day(
        self, owner_id: uuid.UUID, month: int, day: int, *, exclude_year: int, limit: int
    ) -> list[Memory]:
        """Recuerdos de este mismo dia en anos anteriores."""
        ...

    async def list_random(self, owner_id: uuid.UUID, limit: int) -> list[Memory]: ...
