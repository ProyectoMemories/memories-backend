"""Cookie del token de renovación en web (D56, CLAUDE.md §9)."""

from fastapi import Response

from app.modules.auth.entities.user_session import SESSION_LIFETIME

AUTH_PREFIX = "/api/v1/auth"
REFRESH_COOKIE = "memories_refresh"


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    # HttpOnly: el código de la página no la lee. Path: solo viaja a auth.
    response.set_cookie(
        REFRESH_COOKIE,
        refresh_token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        path=AUTH_PREFIX,
        secure=True,
        httponly=True,
        samesite="strict",
    )


def delete_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        REFRESH_COOKIE, path=AUTH_PREFIX, secure=True, httponly=True, samesite="strict"
    )
