"""Formato del token de renovación: "<id de sesión>.<secreto>" (D56, RN-67)."""

import uuid

from app.modules.auth.use_cases.ports import TokenInvalidError


def format_refresh_token(session_id: uuid.UUID, secret: str) -> str:
    return f"{session_id}.{secret}"


def parse_refresh_token(token: str) -> tuple[uuid.UUID, str]:
    session_part, dot, secret = token.partition(".")
    if not dot or not secret:
        raise TokenInvalidError
    try:
        return uuid.UUID(session_part), secret
    except ValueError as error:
        raise TokenInvalidError from error
