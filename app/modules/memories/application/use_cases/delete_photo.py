"""Caso de uso: descartar una fotografia todavia sin recuerdo.

Sirve para cuando alguien sube una foto y cambia de idea antes de guardar. Las
que ya pertenecen a un recuerdo se quitan desde el recuerdo, porque ahi si hay
una regla que respetar (no quedarse sin ninguna).
"""

import uuid

import structlog

from app.core.storage.port import StoragePort
from app.modules.memories.domain.errors import PhotoNotFoundError
from app.modules.memories.domain.repositories.photo_repository import PhotoRepository
from app.shared.errors import ConflictError, StorageError

logger = structlog.get_logger(__name__)


class DeletePhoto:
    def __init__(self, photos: PhotoRepository, storage: StoragePort) -> None:
        self._photos = photos
        self._storage = storage

    async def execute(self, photo_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        photo = await self._photos.get(photo_id, owner_id)
        if photo is None:
            raise PhotoNotFoundError()
        if photo.is_attached:
            raise ConflictError(
                "Esa fotografia pertenece a un recuerdo: quitala desde el recuerdo."
            )

        await self._photos.delete(photo)
        try:
            await self._storage.delete(photo.storage_key)
        except StorageError as exc:
            logger.warning(
                "no_se_pudo_borrar_archivo", storage_key=photo.storage_key, error=str(exc)
            )
