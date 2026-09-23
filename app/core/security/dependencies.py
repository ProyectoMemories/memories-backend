"""Dependencias de autenticacion y autorizacion para la API.

El token de acceso lleva el id y el rol, asi que autenticar no toca la base de
datos. Contrapartida asumida: desactivar a alguien surte efecto cuando vence su
token de acceso (30 minutos como maximo), no al instante.
"""

import uuid
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config.settings import get_settings
from app.core.security.tokens.jwt_service import JWTService
from app.shared.errors import AuthenticationError, PermissionDeniedError
from app.shared.roles import UserRole

bearer_scheme = HTTPBearer(auto_error=False, description="Token de acceso JWT")


@dataclass(frozen=True, slots=True)
class CurrentUser:
    id: uuid.UUID
    role: UserRole

    @property
    def is_superuser(self) -> bool:
        return self.role is UserRole.SUPERUSER


@lru_cache(maxsize=1)
def get_jwt_service() -> JWTService:
    settings = get_settings()
    return JWTService(
        secret_key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        access_token_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        refresh_token_days=settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(bearer_scheme)],
    jwt_service: Annotated[JWTService, Depends(get_jwt_service)],
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthenticationError("Falta el token de acceso.")

    claims = jwt_service.decode(credentials.credentials, expected_type="access")
    try:
        role = UserRole(claims.role)
    except ValueError as exc:
        raise AuthenticationError("Token invalido.") from exc
    return CurrentUser(id=claims.subject, role=role)


CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]


async def require_superuser(current_user: CurrentUserDep) -> CurrentUser:
    if not current_user.is_superuser:
        raise PermissionDeniedError("Esta operacion es solo para el superusuario.")
    return current_user


SuperuserDep = Annotated[CurrentUser, Depends(require_superuser)]
