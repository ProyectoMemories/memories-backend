"""Esquemas HTTP de fotografias."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.modules.memories.domain.entities.photo import Photo


class PhotoResponse(BaseModel):
    id: uuid.UUID
    url: str
    content_type: str
    size_bytes: int
    position: int
    memory_id: uuid.UUID | None
    created_at: datetime

    @classmethod
    def from_entity(cls, photo: Photo, url: str) -> "PhotoResponse":
        return cls(
            id=photo.id,
            url=url,
            content_type=photo.content_type,
            size_bytes=photo.size_bytes,
            position=photo.position,
            memory_id=photo.memory_id,
            created_at=photo.created_at,
        )


class AttachPhotosRequest(BaseModel):
    photo_ids: list[uuid.UUID]
