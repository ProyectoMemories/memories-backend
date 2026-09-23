"""Caso de uso: quitar una fotografia de un recuerdo.

El dominio impide quitar la ultima: un recuerdo sin fotografias no existe.
"""

import uuid

import structlog

from app.core.storage.port import StoragePort
from app.modules.memories.domain.entities.memory import Memory
from app.modules.memories.domain.errors import MemoryNotFoundError
from app.modules.memories.domain.repositories.memory_repository import MemoryRepository
from app.modules.memories.domain.repositories.photo_repository import PhotoRepository
from app.shared.errors import StorageError

logger = structlog.get_logger(__name__)


class RemovePhoto:
    def __init__(
        self,
        memories: MemoryRepository,
        photos: PhotoRepository,
        storage: StoragePort,
    ) -> None:
        self._memories = memories
        self._photos = photos
        self._storage = storage

    async def execute(
        self, memory_id: uuid.UUID, photo_id: uuid.UUID, owner_id: uuid.UUID
    ) -> Memory:
        memory = await self._memories.get(memory_id, owner_id)
        if memory is None:
            raise MemoryNotFoundError()

        photo = memory.remove_photo(photo_id)
        await self._memories.update(memory)
        await self._photos.delete(photo)

        try:
            await self._storage.delete(photo.storage_key)
        except StorageError as exc:
            logger.warning(
                "no_se_pudo_borrar_archivo", storage_key=photo.storage_key, error=str(exc)
            )
        return memory
