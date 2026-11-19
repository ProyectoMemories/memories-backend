"""Puertos de auth: lo que los interactores necesitan del exterior.

Los implementan los adaptadores (gateways y services). Los interactores solo
conocen estas interfaces, nunca SQLAlchemy, PyJWT ni pwdlib.
"""

import uuid
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol

from app.modules.auth.entities.privacy_consent import PrivacyConsent
from app.modules.auth.entities.user import User
from app.modules.auth.entities.user_session import UserSession


class TokenPurpose(StrEnum):
    """Para qué sirve un enlace de correo: uno nunca vale por otro."""

    VERIFY_EMAIL = "verify_email"


class TokenExpiredError(Exception):
    """El token es auténtico pero ya venció."""


class TokenInvalidError(Exception):
    """El token está alterado, mal formado o no es del tipo esperado."""


class UserGateway(Protocol):
    def get(self, user_id: uuid.UUID) -> User | None: ...

    def get_by_email(self, email: str) -> User | None: ...

    def get_by_login(self, identifier: str) -> User | None:
        """Por correo o nombre de usuario, sin importar mayúsculas (RN-06)."""
        ...

    def add(self, user: User, consent: PrivacyConsent) -> None:
        """Lanza UsernameTakenError o EmailTakenError si ya existen."""
        ...

    def save(self, user: User) -> None: ...


class SessionGateway(Protocol):
    def add(self, user_session: UserSession) -> None: ...

    def get(self, session_id: uuid.UUID) -> UserSession | None: ...

    def get_for_update(self, session_id: uuid.UUID) -> UserSession | None:
        """Bloquea la sesión: dos renovaciones con el mismo token van de a una."""
        ...

    def save(self, user_session: UserSession) -> None: ...


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str: ...

    def verify_and_update(
        self, password: str, password_hash: str
    ) -> tuple[bool, str | None]:
        """Si coincide y, cuando el hash usa parámetros viejos, uno nuevo."""
        ...

    def verify_dummy(self, password: str) -> None:
        """Tarda lo mismo que verificar, para no revelar qué cuentas existen."""
        ...


class AccessTokens(Protocol):
    def create(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        lifetime: timedelta,
        now: datetime,
    ) -> str: ...

    def read(self, token: str) -> tuple[uuid.UUID, uuid.UUID]:
        """(id de usuario, id de sesión).

        Lanza TokenExpiredError o TokenInvalidError.
        """
        ...


class EmailLinkTokens(Protocol):
    def create(
        self,
        user_id: uuid.UUID,
        purpose: TokenPurpose,
        lifetime: timedelta,
        now: datetime,
    ) -> str: ...

    def read(self, token: str, purpose: TokenPurpose) -> uuid.UUID:
        """Id del usuario. Lanza TokenExpiredError o TokenInvalidError."""
        ...


class RefreshSecrets(Protocol):
    def new_secret(self) -> str: ...

    def hash(self, secret: str) -> str: ...

    def matches(self, secret: str, stored_hash: str) -> bool: ...
