"""Armado de las respuestas que llevan fotografias.

Cada fotografia necesita una URL, y resolverla es una llamada al
almacenamiento: se hace aqui, en el borde, y no dentro de los casos de uso.
"""

from app.modules.memories.application.photo_url_service import PhotoUrlService
from app.modules.memories.domain.entities.memory import Memory
from app.modules.memories.interfaces.http.schemas.memory_schemas import MemoryResponse
from app.modules.memories.interfaces.http.schemas.photo_schemas import PhotoResponse


async def to_memory_response(memory: Memory, urls: PhotoUrlService) -> MemoryResponse:
    photos = [
        PhotoResponse.from_entity(photo, await urls.url_for(photo)) for photo in memory.photos
    ]
    return MemoryResponse.from_entity(memory, photos)
