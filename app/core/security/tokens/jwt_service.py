"""Emision y validacion de JWT (HS256 por defecto).

El token de acceso es corto y sin estado; el de refresco es largo y si tiene
estado en Redis, para poder revocarlo al cerrar sesion (ver
app/modules/auth/infrastructure/token_store).
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt

from app.shared.errors import AuthenticationError

TokenType = Literal["access", "refresh"]


@dataclass(frozen=True, slots=True)
class IssuedToken:
    token: str
    jti: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class TokenClaims:
    subject: uuid.UUID
    role: str
    token_type: TokenType
    jti: str
    expires_at: datetime


class JWTService:
    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_minutes: int = 30,
        refresh_token_days: int = 30,
    ) -> None:
        self._secret = secret_key
        self._algorithm = algorithm
        self._access_delta = timedelta(minutes=access_token_minutes)
        self._refresh_delta = timedelta(days=refresh_token_days)

    @property
    def refresh_token_ttl_seconds(self) -> int:
        return int(self._refresh_delta.total_seconds())

    @property
    def access_token_ttl_seconds(self) -> int:
        return int(self._access_delta.total_seconds())

    def create_access_token(self, subject: uuid.UUID, role: str) -> IssuedToken:
        return self._create(subject, role, "access", self._access_delta)

    def create_refresh_token(self, subject: uuid.UUID, role: str) -> IssuedToken:
        return self._create(subject, role, "refresh", self._refresh_delta)

    def decode(self, token: str, *, expected_type: TokenType) -> TokenClaims:
        try:
            payload: dict[str, Any] = jwt.decode(token, self._secret, algorithms=[self._algorithm])
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("La sesion expiro. Inicia sesion de nuevo.") from exc
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("Token invalido.") from exc

        if payload.get("type") != expected_type:
            raise AuthenticationError("Token invalido para esta operacion.")

        try:
            return TokenClaims(
                subject=uuid.UUID(payload["sub"]),
                role=str(payload["role"]),
                token_type=expected_type,
                jti=str(payload["jti"]),
                expires_at=datetime.fromtimestamp(float(payload["exp"]), tz=UTC),
            )
        except (KeyError, ValueError) as exc:
            raise AuthenticationError("Token invalido.") from exc

    def _create(
        self, subject: uuid.UUID, role: str, token_type: TokenType, delta: timedelta
    ) -> IssuedToken:
        now = datetime.now(tz=UTC)
        expires_at = now + delta
        jti = uuid.uuid4().hex
        payload = {
            "sub": str(subject),
            "role": role,
            "type": token_type,
            "jti": jti,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }
        token = jwt.encode(payload, self._secret, algorithm=self._algorithm)
        return IssuedToken(token=token, jti=jti, expires_at=expires_at)
