"""Caso de uso: borrar un recuerdo (capacidad CP-04).

Se borra de verdad, no con una marca: el PRD promete que el recuerdo es privado
y que el usuario manda sobre el. Los archivos del almacenamiento se borran
despues de la base de datos; si esa segunda parte falla, quedan huerfanos, que
es preferible a una fila que apunta a una foto que ya no existe.
"""

import uuid

import structlog

from app.core.storage.port import StoragePort
from app.modules.memories.domain.errors import MemoryNotFoundError
from app.modules.memories.domain.repositories.memory_repository import MemoryRepository
from app.shared.errors import StorageError

logger = structlog.get_logger(__name__)


class DeleteMemory:
    def __init__(self, memories: MemoryRepository, storage: StoragePort) -> None:
        self._memories = memories
        self._storage = storage

    async def execute(self, memory_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        memory = await self._memories.get(memory_id, owner_id)
        if memory is None:
            raise MemoryNotFoundError()

        storage_keys = [photo.storage_key for photo in memory.photos]
        await self._memories.delete(memory)

        for key in storage_keys:
            try:
                await self._storage.delete(key)
            except StorageError as exc:
                logger.warning("no_se_pudo_borrar_archivo", storage_key=key, error=str(exc))
