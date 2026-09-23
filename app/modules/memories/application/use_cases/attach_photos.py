"""Caso de uso: anadir fotografias a un recuerdo existente."""

import uuid
from dataclasses import dataclass

from app.modules.memories.domain.entities.memory import Memory
from app.modules.memories.domain.errors import MemoryNotFoundError, PhotoNotFoundError
from app.modules.memories.domain.repositories.memory_repository import MemoryRepository
from app.modules.memories.domain.repositories.photo_repository import PhotoRepository


@dataclass(frozen=True, slots=True)
class AttachPhotosCommand:
    memory_id: uuid.UUID
    owner_id: uuid.UUID
    photo_ids: list[uuid.UUID]


class AttachPhotos:
    def __init__(
        self, memories: MemoryRepository, photos: PhotoRepository, max_photos: int
    ) -> None:
        self._memories = memories
        self._photos = photos
        self._max_photos = max_photos

    async def execute(self, command: AttachPhotosCommand) -> Memory:
        memory = await self._memories.get(command.memory_id, command.owner_id)
        if memory is None:
            raise MemoryNotFoundError()

        photos = await self._photos.get_many(command.photo_ids, command.owner_id)
        if len(photos) != len(set(command.photo_ids)):
            raise PhotoNotFoundError("Alguna de las fotografias no existe.")

        memory.add_photos(photos, max_photos=self._max_photos)
        await self._memories.update(memory)
        return memory
