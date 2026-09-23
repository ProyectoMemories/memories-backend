"""Caso de uso: crear un recuerdo (capacidad CP-01)."""

import uuid
from dataclasses import dataclass
from datetime import date

from app.modules.memories.domain.entities.memory import Memory
from app.modules.memories.domain.errors import PhotoNotFoundError
from app.modules.memories.domain.repositories.memory_repository import MemoryRepository
from app.modules.memories.domain.repositories.photo_repository import PhotoRepository


@dataclass(frozen=True, slots=True)
class CreateMemoryCommand:
    owner_id: uuid.UUID
    title: str
    moment_date: date
    photo_ids: list[uuid.UUID]
    description: str | None = None


class CreateMemory:
    def __init__(
        self, memories: MemoryRepository, photos: PhotoRepository, max_photos: int
    ) -> None:
        self._memories = memories
        self._photos = photos
        self._max_photos = max_photos

    async def execute(self, command: CreateMemoryCommand) -> Memory:
        photos = await self._photos.get_many(command.photo_ids, command.owner_id)
        if len(photos) != len(set(command.photo_ids)):
            # Falta alguna: o no existe, o es de otra persona. Se responde igual
            # en los dos casos para no revelar la existencia de archivos ajenos.
            raise PhotoNotFoundError("Alguna de las fotografias no existe.")

        memory = Memory.create(
            owner_id=command.owner_id,
            title=command.title,
            moment_date=command.moment_date,
            description=command.description,
            photos=photos,
            max_photos=self._max_photos,
        )
        await self._memories.add(memory)
        return memory
