"""Composicion de dependencias del modulo de usuarios.

Todo el cableado vive aqui, no en el router: en CRIS esa funcion acabo dentro
del controlador y llego a ocupar cien lineas.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_session
from app.modules.users.application.use_cases.get_user_profile import GetUserProfile
from app.modules.users.application.use_cases.list_users import ListUsers
from app.modules.users.application.use_cases.update_user_profile import UpdateUserProfile
from app.modules.users.domain.repositories.user_repository import UserRepository
from app.modules.users.infrastructure.repositories.sqlalchemy_user_repository import (
    SQLAlchemyUserRepository,
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_user_repository(session: SessionDep) -> UserRepository:
    return SQLAlchemyUserRepository(session)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]


def get_user_profile_use_case(users: UserRepositoryDep) -> GetUserProfile:
    return GetUserProfile(users)


def update_user_profile_use_case(users: UserRepositoryDep) -> UpdateUserProfile:
    return UpdateUserProfile(users)


def list_users_use_case(users: UserRepositoryDep) -> ListUsers:
    return ListUsers(users)
