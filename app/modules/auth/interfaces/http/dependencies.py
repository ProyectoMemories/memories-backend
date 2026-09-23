"""Composicion de dependencias del modulo de autenticacion."""

from typing import Annotated

from fastapi import Depends

from app.core.cache.factory import get_cache
from app.core.cache.port import CachePort
from app.core.security.dependencies import get_jwt_service
from app.core.security.hashing.factory import get_password_hashing_service
from app.core.security.hashing.service import PasswordHashingService
from app.core.security.tokens.jwt_service import JWTService
from app.modules.auth.application.ports import RefreshTokenStore
from app.modules.auth.application.use_cases.authenticate_user import AuthenticateUser
from app.modules.auth.application.use_cases.logout_user import LogoutUser
from app.modules.auth.application.use_cases.refresh_session import RefreshSession
from app.modules.auth.application.use_cases.register_user import RegisterUser
from app.modules.auth.infrastructure.token_store.cache_refresh_token_store import (
    CacheRefreshTokenStore,
)
from app.modules.users.domain.repositories.user_repository import UserRepository
from app.modules.users.interfaces.http.dependencies import get_user_repository

UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
HashingDep = Annotated[PasswordHashingService, Depends(get_password_hashing_service)]
JWTDep = Annotated[JWTService, Depends(get_jwt_service)]
CacheDep = Annotated[CachePort, Depends(get_cache)]


def get_refresh_token_store(cache: CacheDep) -> RefreshTokenStore:
    return CacheRefreshTokenStore(cache)


RefreshTokenStoreDep = Annotated[RefreshTokenStore, Depends(get_refresh_token_store)]


def register_user_use_case(users: UserRepositoryDep, hashing: HashingDep) -> RegisterUser:
    return RegisterUser(users, hashing)


def authenticate_user_use_case(
    users: UserRepositoryDep,
    hashing: HashingDep,
    jwt_service: JWTDep,
    refresh_tokens: RefreshTokenStoreDep,
) -> AuthenticateUser:
    return AuthenticateUser(users, hashing, jwt_service, refresh_tokens)


def refresh_session_use_case(
    users: UserRepositoryDep,
    jwt_service: JWTDep,
    refresh_tokens: RefreshTokenStoreDep,
) -> RefreshSession:
    return RefreshSession(users, jwt_service, refresh_tokens)


def logout_user_use_case(
    jwt_service: JWTDep,
    refresh_tokens: RefreshTokenStoreDep,
) -> LogoutUser:
    return LogoutUser(jwt_service, refresh_tokens)
