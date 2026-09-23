"""Implementacion del puerto MemoryRepository sobre SQLAlchemy.

Toda consulta filtra por owner_id. No es una precaucion opcional: es la
privacidad por defecto que promete el PRD, y hay un test que intenta leer un
recuerdo ajeno y exige un 404.
"""

import uuid
from datetime import date

from sqlalchemy import extract, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.memories.domain.entities.memory import Memory
from app.modules.memories.infrastructure.mappers import memory_mapper
from app.modules.memories.infrastructure.models.memory_model import MemoryModel
from app.modules.memories.infrastructure.models.photo_model import PhotoModel


class SQLAlchemyMemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, memory: Memory) -> None:
        self._session.add(memory_mapper.to_model(memory))
        await self._session.flush()
        await self._sync_photos(memory)

    async def update(self, memory: Memory) -> None:
        model = await self._session.get(MemoryModel, memory.id)
        if model is None:
            return
        memory_mapper.apply_changes(memory, model)
        await self._session.flush()
        await self._sync_photos(memory)

    async def delete(self, memory: Memory) -> None:
        model = await self._session.get(MemoryModel, memory.id)
        if model is None:
            return
        # Las fotografias caen con el recuerdo (ON DELETE CASCADE).
        await self._session.delete(model)
        await self._session.flush()

    async def get(self, memory_id: uuid.UUID, owner_id: uuid.UUID) -> Memory | None:
        stmt = select(MemoryModel).where(
            MemoryModel.id == memory_id, MemoryModel.owner_id == owner_id
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return memory_mapper.to_entity(model) if model else None

    async def list_for_owner(
        self,
        owner_id: uuid.UUID,
        *,
        offset: int,
        limit: int,
        date_from: date | None = None,
        date_to: date | None = None,
        search: str | None = None,
    ) -> tuple[list[Memory], int]:
        filters = [MemoryModel.owner_id == owner_id]
        if date_from is not None:
            filters.append(MemoryModel.moment_date >= date_from)
        if date_to is not None:
            filters.append(MemoryModel.moment_date <= date_to)
        if search:
            pattern = f"%{search.strip()}%"
            filters.append(
                or_(MemoryModel.title.ilike(pattern), MemoryModel.description.ilike(pattern))
            )

        total = (
            await self._session.execute(
                select(func.count()).select_from(MemoryModel).where(*filters)
            )
        ).scalar_one()

        stmt = (
            select(MemoryModel)
            .where(*filters)
            .order_by(MemoryModel.moment_date.desc(), MemoryModel.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [memory_mapper.to_entity(model) for model in models], int(total)

    async def count_by_day(self, owner_id: uuid.UUID, year: int, month: int) -> dict[date, int]:
        stmt = (
            select(MemoryModel.moment_date, func.count())
            .where(
                MemoryModel.owner_id == owner_id,
                extract("year", MemoryModel.moment_date) == year,
                extract("month", MemoryModel.moment_date) == month,
            )
            .group_by(MemoryModel.moment_date)
        )
        rows = (await self._session.execute(stmt)).all()
        return {row[0]: int(row[1]) for row in rows}

    async def list_on_this_day(
        self, owner_id: uuid.UUID, month: int, day: int, *, exclude_year: int, limit: int
    ) -> list[Memory]:
        stmt = (
            select(MemoryModel)
            .where(
                MemoryModel.owner_id == owner_id,
                extract("month", MemoryModel.moment_date) == month,
                extract("day", MemoryModel.moment_date) == day,
                extract("year", MemoryModel.moment_date) != exclude_year,
            )
            .order_by(MemoryModel.moment_date.desc())
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [memory_mapper.to_entity(model) for model in models]

    async def list_random(self, owner_id: uuid.UUID, limit: int) -> list[Memory]:
        # func.random() ordena toda la tabla del usuario. Con miles de recuerdos
        # por persona habria que cambiarlo; con los del MVP sobra.
        stmt = (
            select(MemoryModel)
            .where(MemoryModel.owner_id == owner_id)
            .order_by(func.random())
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [memory_mapper.to_entity(model) for model in models]

    async def _sync_photos(self, memory: Memory) -> None:
        """Lleva a la tabla el orden y la pertenencia que decidio el dominio."""
        for photo in memory.photos:
            await self._session.execute(
                update(PhotoModel)
                .where(PhotoModel.id == photo.id, PhotoModel.owner_id == memory.owner_id)
                .values(memory_id=photo.memory_id, position=photo.position)
            )
        await self._session.flush()
