"""Puerto del repositorio de fotografias."""

import uuid
from collections.abc import Sequence
from typing import Protocol

from app.modules.memories.domain.entities.photo import Photo


class PhotoRepository(Protocol):
    async def add(self, photo: Photo) -> None: ...

    async def update(self, photo: Photo) -> None: ...

    async def delete(self, photo: Photo) -> None: ...

    async def get(self, photo_id: uuid.UUID, owner_id: uuid.UUID) -> Photo | None: ...

    async def get_many(self, photo_ids: Sequence[uuid.UUID], owner_id: uuid.UUID) -> list[Photo]:
        """Devuelve solo las fotografias de ese propietario, en el orden pedido."""
        ...
