"""Caso de uso: subir una fotografia.

La foto se sube antes de que exista el recuerdo (la app va subiendo mientras la
persona escribe). Queda "suelta" hasta que se crea el recuerdo o se asocia a
uno existente.
"""

import uuid
from dataclasses import dataclass

from app.core.storage.port import StoragePort
from app.modules.memories.application.image_validator import PhotoUploadRules, validate_image
from app.modules.memories.domain.entities.photo import Photo
from app.modules.memories.domain.repositories.photo_repository import PhotoRepository


@dataclass(frozen=True, slots=True)
class UploadPhotoCommand:
    owner_id: uuid.UUID
    content_type: str
    data: bytes


class UploadPhoto:
    def __init__(
        self, photos: PhotoRepository, storage: StoragePort, rules: PhotoUploadRules
    ) -> None:
        self._photos = photos
        self._storage = storage
        self._rules = rules

    async def execute(self, command: UploadPhotoCommand) -> Photo:
        extension = validate_image(command.data, command.content_type, self._rules)

        # La clave incluye al propietario: aisla los archivos por usuario y hace
        # evidente de quien es cada objeto al mirar el bucket.
        photo_id = uuid.uuid4()
        storage_key = f"{command.owner_id}/{photo_id.hex}{extension}"

        stored = await self._storage.save(
            storage_key, command.data, command.content_type.split(";")[0].strip().lower()
        )
        photo = Photo.register(
            owner_id=command.owner_id,
            storage_key=stored.key,
            content_type=stored.content_type,
            size_bytes=stored.size_bytes,
            checksum_sha256=stored.checksum_sha256,
            photo_id=photo_id,
        )
        await self._photos.add(photo)
        return photo
