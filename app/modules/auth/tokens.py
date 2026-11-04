"""Tokens firmados: enlaces de correo y JWT de acceso (specs/auth/design.md §3-4).

No se guardan en la base (RN-19, D56): basta con la firma y el vencimiento.
Todos usan la misma SECRET_KEY, así que cada uno dice qué es: los del correo
llevan `purpose` y los de acceso, `type: "access"`. Así uno nunca sirve como
el otro.
"""

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta
from enum import StrEnum

import jwt

_ALGORITHM = "HS256"
_ACCESS_TYPE = "access"


class TokenPurpose(StrEnum):
    VERIFY_EMAIL = "verify_email"


class ExpiredTokenError(Exception):
    pass


class InvalidTokenError(Exception):
    pass


def create_email_token(
    user_id: uuid.UUID,
    purpose: TokenPurpose,
    lifetime: timedelta,
    secret_key: str,
    now: datetime,
) -> str:
    claims = {
        "sub": str(user_id),
        "purpose": purpose.value,
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(claims, secret_key, algorithm=_ALGORITHM)


def read_email_token(token: str, purpose: TokenPurpose, secret_key: str) -> uuid.UUID:
    """Valida firma, vencimiento y propósito. Devuelve el id del usuario."""
    try:
        claims = jwt.decode(
            token,
            secret_key,
            algorithms=[_ALGORITHM],
            options={"require": ["sub", "purpose", "exp"]},
        )
    except jwt.ExpiredSignatureError as error:
        raise ExpiredTokenError from error
    except jwt.InvalidTokenError as error:
        raise InvalidTokenError from error

    if claims["purpose"] != purpose.value:
        raise InvalidTokenError
    try:
        return uuid.UUID(claims["sub"])
    except ValueError as error:
        raise InvalidTokenError from error


# ─── Token de acceso (D56) ─────────────────────────────────────────────────


def create_access_token(
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    lifetime: timedelta,
    secret_key: str,
    now: datetime,
) -> str:
    claims = {
        "sub": str(user_id),
        "sid": str(session_id),
        "type": _ACCESS_TYPE,
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(claims, secret_key, algorithm=_ALGORITHM)


def read_access_token(token: str, secret_key: str) -> tuple[uuid.UUID, uuid.UUID]:
    """Valida firma, vencimiento y tipo. Devuelve (id de usuario, id de sesión)."""
    try:
        claims = jwt.decode(
            token,
            secret_key,
            algorithms=[_ALGORITHM],
            options={"require": ["sub", "sid", "type", "exp"]},
        )
    except jwt.ExpiredSignatureError as error:
        raise ExpiredTokenError from error
    except jwt.InvalidTokenError as error:
        raise InvalidTokenError from error

    if claims["type"] != _ACCESS_TYPE:
        raise InvalidTokenError
    try:
        return uuid.UUID(claims["sub"]), uuid.UUID(claims["sid"])
    except ValueError as error:
        raise InvalidTokenError from error


# ─── Token de renovación: "<id de sesión>.<secreto>" (D56, RN-67) ──────────


def new_refresh_secret() -> str:
    return secrets.token_urlsafe(32)  # 256 bits


def format_refresh_token(session_id: uuid.UUID, secret: str) -> str:
    return f"{session_id}.{secret}"


def parse_refresh_token(token: str) -> tuple[uuid.UUID, str]:
    session_part, dot, secret = token.partition(".")
    if not dot or not secret:
        raise InvalidTokenError
    try:
        return uuid.UUID(session_part), secret
    except ValueError as error:
        raise InvalidTokenError from error


def hash_refresh_secret(secret: str) -> str:
    # El secreto es aleatorio y largo: no necesita un hash lento (design.md §3).
    return hashlib.sha256(secret.encode()).hexdigest()


def refresh_secret_matches(secret: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_refresh_secret(secret), stored_hash)
