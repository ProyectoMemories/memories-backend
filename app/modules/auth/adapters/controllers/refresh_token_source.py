"""De dónde viene el token de renovación: cuerpo (Android) o cookie (web)."""

from fastapi import Request

from app.modules.auth.adapters.controllers.requests import RefreshTokenRequest
from app.modules.auth.adapters.presenters.refresh_cookie import REFRESH_COOKIE
from app.modules.auth.entities.user_session import ClientPlatform
from app.shared.entities.errors import ForbiddenError


class OriginNotAllowedError(ForbiddenError):
    code = "origin_not_allowed"
    message = "Esta petición solo se acepta desde la app web de Memories."


def refresh_token_from(
    request: Request, body: RefreshTokenRequest | None
) -> tuple[str | None, ClientPlatform]:
    if body is not None:
        return body.refresh_token, ClientPlatform.ANDROID
    # El navegador manda la cookie solo: hay que comprobar que la petición viene
    # de la app web y no de otro sitio (CSRF, CLAUDE.md §9).
    if request.headers.get("origin") != request.app.state.settings.web_app_origin:
        raise OriginNotAllowedError
    return request.cookies.get(REFRESH_COOKIE), ClientPlatform.WEB
