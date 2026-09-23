"""Caso de uso: descargar el contenido de una fotografia por la propia API.

Es la alternativa a la URL firmada, para cuando el almacenamiento no las emite
(disco local) o el cliente prefiere pasar por la API.
"""

import uuid
from dataclasses import dataclass

from app.core.storage.port import StoragePort
from app.modules.memories.domain.errors import PhotoNotFoundError
from app.modules.memories.domain.repositories.photo_repository import PhotoRepository


@dataclass(frozen=True, slots=True)
class PhotoContent:
    data: bytes
    content_type: str


class GetPhotoContent:
    def __init__(self, photos: PhotoRepository, storage: StoragePort) -> None:
        self._photos = photos
        self._storage = storage

    async def execute(self, photo_id: uuid.UUID, owner_id: uuid.UUID) -> PhotoContent:
        photo = await self._photos.get(photo_id, owner_id)
        if photo is None:
            raise PhotoNotFoundError()
        data = await self._storage.get(photo.storage_key)
        return PhotoContent(data=data, content_type=photo.content_type)
