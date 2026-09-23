"""Implementacion del puerto UserRepository sobre SQLAlchemy."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.domain.entities.user import User
from app.modules.users.domain.value_objects.email import Email
from app.modules.users.infrastructure.mappers.user_mapper import apply_changes, to_entity, to_model
from app.modules.users.infrastructure.models.user_model import UserModel


class SQLAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        self._session.add(to_model(user))
        await self._session.flush()

    async def update(self, user: User) -> None:
        model = await self._session.get(UserModel, user.id)
        if model is None:
            return
        apply_changes(user, model)
        await self._session.flush()

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return to_entity(model) if model else None

    async def get_by_email(self, email: Email) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email.value)
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return to_entity(model) if model else None

    async def exists_with_email(self, email: Email) -> bool:
        stmt = select(func.count()).select_from(UserModel).where(UserModel.email == email.value)
        return bool((await self._session.execute(stmt)).scalar_one())

    async def list_all(self, offset: int, limit: int) -> tuple[list[User], int]:
        total = (
            await self._session.execute(select(func.count()).select_from(UserModel))
        ).scalar_one()
        stmt = select(UserModel).order_by(UserModel.created_at.desc()).offset(offset).limit(limit)
        models = (await self._session.execute(stmt)).scalars().all()
        return [to_entity(model) for model in models], int(total)
