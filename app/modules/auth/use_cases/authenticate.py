"""Caso de uso: identificar al usuario de una petición (RN-67, D56).

Exige que la cuenta siga activa y que su sesión siga abierta: así cerrar sesión
o cambiar la contraseña corta también el token de acceso.
"""

import uuid
from dataclasses import dataclass

from app.modules.auth.use_cases.errors import (
    AccessTokenExpiredError,
    NotAuthenticatedError,
)
from app.modules.auth.use_cases.ports import (
    AccessTokens,
    SessionGateway,
    TokenExpiredError,
    TokenInvalidError,
    UserGateway,
)
from app.shared.entities.clock import Clock


@dataclass(frozen=True)
class AuthenticatedUser:
    """Lo que otros módulos saben del usuario actual."""

    id: uuid.UUID
    username: str
    email: str


class Authenticate:
    def __init__(
        self,
        users: UserGateway,
        sessions: SessionGateway,
        access_tokens: AccessTokens,
        clock: Clock,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._access_tokens = access_tokens
        self._clock = clock

    def execute(self, access_token: str) -> AuthenticatedUser:
        user_id, session_id = self._read(access_token)
        user_session = self._sessions.get(session_id)
        if (
            user_session is None
            or not user_session.belongs_to(user_id)
            or not user_session.is_open(self._clock())
        ):
            raise NotAuthenticatedError
        user = self._users.get(user_id)
        if user is None or not user.is_active:
            raise NotAuthenticatedError
        return AuthenticatedUser(id=user.id, username=user.username, email=user.email)

    def _read(self, access_token: str) -> tuple[uuid.UUID, uuid.UUID]:
        try:
            return self._access_tokens.read(access_token)
        except TokenExpiredError as error:
            raise AccessTokenExpiredError from error
        except TokenInvalidError as error:
            raise NotAuthenticatedError from error
