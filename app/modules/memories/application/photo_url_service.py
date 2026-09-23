"""Resuelve la URL con la que el cliente descarga una fotografia.

Con MinIO o S3 se entrega una URL firmada y temporal: el telefono descarga
directo del almacenamiento y la API no mueve los bytes. Cuando el backend de
almacenamiento no firma URLs (disco local), se devuelve el endpoint propio que
sirve el archivo.
"""

from app.core.storage.port import StoragePort
from app.modules.memories.domain.entities.photo import Photo


class PhotoUrlService:
    def __init__(self, storage: StoragePort, raw_url_template: str) -> None:
        self._storage = storage
        self._raw_url_template = raw_url_template

    async def url_for(self, photo: Photo) -> str:
        presigned = await self._storage.presigned_url(photo.storage_key)
        if presigned:
            return presigned
        return self._raw_url_template.format(photo_id=photo.id)
