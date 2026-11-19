"""Tokens firmados con PyJWT: enlaces de correo y token de acceso (D56).

No se guardan (RN-19, D56). Todos usan la misma SECRET_KEY, así que cada uno
dice qué es: los del correo llevan `purpose` y los de acceso,
`type: "access"`. Así uno nunca sirve como el otro.
"""

import uuid
from datetime import datetime, timedelta
from typing import Any

import jwt

from app.modules.auth.use_cases.ports import (
    TokenExpiredError,
    TokenInvalidError,
    TokenPurpose,
)

_ALGORITHM = "HS256"
_ACCESS_TYPE = "access"


def _decode(token: str, secret_key: str, required: list[str]) -> dict[str, Any]:
    try:
        return jwt.decode(
            token, secret_key, algorithms=[_ALGORITHM], options={"require": required}
        )
    except jwt.ExpiredSignatureError as error:
        raise TokenExpiredError from error
    except jwt.InvalidTokenError as error:
        raise TokenInvalidError from error


def _uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as error:
        raise TokenInvalidError from error


class JwtEmailLinkTokens:
    def __init__(self, secret_key: str) -> None:
        self._secret_key = secret_key

    def create(
        self,
        user_id: uuid.UUID,
        purpose: TokenPurpose,
        lifetime: timedelta,
        now: datetime,
    ) -> str:
        claims = {
            "sub": str(user_id),
            "purpose": purpose.value,
            "iat": now,
            "exp": now + lifetime,
        }
        return jwt.encode(claims, self._secret_key, algorithm=_ALGORITHM)

    def read(self, token: str, purpose: TokenPurpose) -> uuid.UUID:
        claims = _decode(token, self._secret_key, ["sub", "purpose", "exp"])
        if claims["purpose"] != purpose.value:
            raise TokenInvalidError
        return _uuid(claims["sub"])


class JwtAccessTokens:
    def __init__(self, secret_key: str) -> None:
        self._secret_key = secret_key

    def create(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        lifetime: timedelta,
        now: datetime,
    ) -> str:
        claims = {
            "sub": str(user_id),
            "sid": str(session_id),
            "type": _ACCESS_TYPE,
            "iat": now,
            "exp": now + lifetime,
        }
        return jwt.encode(claims, self._secret_key, algorithm=_ALGORITHM)

    def read(self, token: str) -> tuple[uuid.UUID, uuid.UUID]:
        claims = _decode(token, self._secret_key, ["sub", "sid", "type", "exp"])
        if claims["type"] != _ACCESS_TYPE:
            raise TokenInvalidError
        return _uuid(claims["sub"]), _uuid(claims["sid"])
