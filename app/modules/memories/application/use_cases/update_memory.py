"""Caso de uso: editar un recuerdo (capacidad CP-04)."""

import uuid
from dataclasses import dataclass
from datetime import date

from app.modules.memories.domain.entities.memory import Memory
from app.modules.memories.domain.errors import MemoryNotFoundError
from app.modules.memories.domain.repositories.memory_repository import MemoryRepository


@dataclass(frozen=True, slots=True)
class UpdateMemoryCommand:
    memory_id: uuid.UUID
    owner_id: uuid.UUID
    title: str | None = None
    moment_date: date | None = None
    description: str | None = None
    clear_description: bool = False


class UpdateMemory:
    def __init__(self, memories: MemoryRepository) -> None:
        self._memories = memories

    async def execute(self, command: UpdateMemoryCommand) -> Memory:
        memory = await self._memories.get(command.memory_id, command.owner_id)
        if memory is None:
            raise MemoryNotFoundError()

        memory.update_details(
            title=command.title,
            moment_date=command.moment_date,
            description=command.description,
            clear_description=command.clear_description,
        )
        await self._memories.update(memory)
        return memory
