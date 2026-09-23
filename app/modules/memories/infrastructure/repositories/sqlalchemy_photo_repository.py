"""Implementacion del puerto PhotoRepository sobre SQLAlchemy."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.memories.domain.entities.photo import Photo
from app.modules.memories.infrastructure.mappers import photo_mapper
from app.modules.memories.infrastructure.models.photo_model import PhotoModel


class SQLAlchemyPhotoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, photo: Photo) -> None:
        self._session.add(photo_mapper.to_model(photo))
        await self._session.flush()

    async def update(self, photo: Photo) -> None:
        model = await self._session.get(PhotoModel, photo.id)
        if model is None:
            return
        photo_mapper.apply_changes(photo, model)
        await self._session.flush()

    async def delete(self, photo: Photo) -> None:
        model = await self._session.get(PhotoModel, photo.id)
        if model is None:
            return
        await self._session.delete(model)
        await self._session.flush()

    async def get(self, photo_id: uuid.UUID, owner_id: uuid.UUID) -> Photo | None:
        stmt = select(PhotoModel).where(PhotoModel.id == photo_id, PhotoModel.owner_id == owner_id)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return photo_mapper.to_entity(model) if model else None

    async def get_many(self, photo_ids: Sequence[uuid.UUID], owner_id: uuid.UUID) -> list[Photo]:
        if not photo_ids:
            return []
        stmt = select(PhotoModel).where(
            PhotoModel.id.in_(list(photo_ids)), PhotoModel.owner_id == owner_id
        )
        models = (await self._session.execute(stmt)).scalars().all()
        by_id = {model.id: model for model in models}
        # Se respeta el orden en el que llegaron: es el que eligio la persona.
        return [photo_mapper.to_entity(by_id[pid]) for pid in photo_ids if pid in by_id]
