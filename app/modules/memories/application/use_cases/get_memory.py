"""Caso de uso: ver el detalle de un recuerdo (capacidad CP-03)."""

import uuid

from app.modules.memories.domain.entities.memory import Memory
from app.modules.memories.domain.errors import MemoryNotFoundError
from app.modules.memories.domain.repositories.memory_repository import MemoryRepository


class GetMemory:
    def __init__(self, memories: MemoryRepository) -> None:
        self._memories = memories

    async def execute(self, memory_id: uuid.UUID, owner_id: uuid.UUID) -> Memory:
        # Pedir un recuerdo ajeno responde "no existe", no "no puedes": asi no se
        # confirma que ese identificador exista.
        memory = await self._memories.get(memory_id, owner_id)
        if memory is None:
            raise MemoryNotFoundError()
        return memory
