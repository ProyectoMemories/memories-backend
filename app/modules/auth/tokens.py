"""Tokens firmados de los enlaces de correo (specs/auth/design.md §4).

No se guardan en la base (RN-19): basta con la firma y el vencimiento. Cada token
lleva su propósito para que uno de verificación no sirva para otra cosa.
"""

import uuid
from datetime import datetime, timedelta
from enum import StrEnum

import jwt

_ALGORITHM = "HS256"


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
