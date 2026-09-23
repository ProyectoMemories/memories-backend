"""Entidad Fotografia.

Una fotografia se sube primero y se asocia despues: asi la app puede ir
subiendo mientras la persona escribe el titulo y la descripcion. Mientras no
pertenece a ningun recuerdo se queda "suelta" (memory_id = None).
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.modules.memories.domain.errors import PhotoAlreadyAttachedError


def _now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(slots=True)
class Photo:
    id: uuid.UUID
    owner_id: uuid.UUID
    storage_key: str
    content_type: str
    size_bytes: int
    checksum_sha256: str
    memory_id: uuid.UUID | None = None
    position: int = 0
    created_at: datetime = field(default_factory=_now)

    @classmethod
    def register(
        cls,
        *,
        owner_id: uuid.UUID,
        storage_key: str,
        content_type: str,
        size_bytes: int,
        checksum_sha256: str,
        photo_id: uuid.UUID | None = None,
    ) -> "Photo":
        return cls(
            id=photo_id or uuid.uuid4(),
            owner_id=owner_id,
            storage_key=storage_key,
            content_type=content_type,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
        )

    @property
    def is_attached(self) -> bool:
        return self.memory_id is not None

    def belongs_to(self, owner_id: uuid.UUID) -> bool:
        return self.owner_id == owner_id

    def attach_to(self, memory_id: uuid.UUID, position: int) -> None:
        if self.is_attached and self.memory_id != memory_id:
            raise PhotoAlreadyAttachedError()
        self.memory_id = memory_id
        self.position = position

    def detach(self) -> None:
        self.memory_id = None
        self.position = 0
