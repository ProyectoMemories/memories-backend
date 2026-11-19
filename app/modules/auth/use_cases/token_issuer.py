"""Arma los tokens que recibe la app al iniciar sesión o renovar (D56)."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.modules.auth.entities.user_session import ClientPlatform, UserSession
from app.modules.auth.use_cases.ports import AccessTokens
from app.modules.auth.use_cases.refresh_token import format_refresh_token

ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    expires_in: int  # segundos
    refresh_token: str
    platform: ClientPlatform


class TokenIssuer:
    def __init__(self, access_tokens: AccessTokens) -> None:
        self._access_tokens = access_tokens

    def issue(
        self, user_session: UserSession, secret: str, now: datetime
    ) -> IssuedTokens:
        access_token = self._access_tokens.create(
            user_session.user_id, user_session.id, ACCESS_TOKEN_LIFETIME, now
        )
        return IssuedTokens(
            access_token=access_token,
            expires_in=int(ACCESS_TOKEN_LIFETIME.total_seconds()),
            refresh_token=format_refresh_token(user_session.id, secret),
            platform=user_session.platform,
        )
