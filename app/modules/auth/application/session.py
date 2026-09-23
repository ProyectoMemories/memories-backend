"""Resultado comun de iniciar o renovar una sesion."""

from dataclasses import dataclass

from app.modules.users.domain.entities.user import User


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    user: User
    access_token: str
    refresh_token: str
    access_token_expires_in: int
