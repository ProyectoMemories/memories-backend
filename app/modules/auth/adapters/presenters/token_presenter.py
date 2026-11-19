"""Presenta los tokens según la plataforma: en el cuerpo (Android) o en cookie (web)."""

from fastapi import Response

from app.modules.auth.adapters.presenters.refresh_cookie import set_refresh_cookie
from app.modules.auth.adapters.presenters.responses import TokenResponse
from app.modules.auth.entities.user_session import ClientPlatform
from app.modules.auth.use_cases.token_issuer import IssuedTokens


def present_tokens(issued: IssuedTokens, response: Response) -> TokenResponse:
    if issued.platform is ClientPlatform.ANDROID:
        return TokenResponse(
            access_token=issued.access_token,
            expires_in=issued.expires_in,
            refresh_token=issued.refresh_token,
        )
    set_refresh_cookie(response, issued.refresh_token)
    return TokenResponse(access_token=issued.access_token, expires_in=issued.expires_in)
