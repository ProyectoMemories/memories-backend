"""Caso de uso: renovar la sesión rotando el token (HU-04; D56, RN-67)."""

from dataclasses import dataclass
from datetime import datetime

from app.modules.auth.entities.user_session import ClientPlatform, UserSession
from app.modules.auth.use_cases.errors import InvalidRefreshTokenError
from app.modules.auth.use_cases.ports import (
    RefreshSecrets,
    SessionGateway,
    TokenInvalidError,
    UserGateway,
)
from app.modules.auth.use_cases.refresh_token import parse_refresh_token
from app.modules.auth.use_cases.token_issuer import IssuedTokens, TokenIssuer
from app.shared.entities.clock import Clock
from app.shared.use_cases.ports import UnitOfWork


@dataclass(frozen=True)
class RefreshSessionInput:
    refresh_token: str | None
    platform: ClientPlatform


class RefreshSession:
    def __init__(
        self,
        users: UserGateway,
        sessions: SessionGateway,
        unit_of_work: UnitOfWork,
        refresh_secrets: RefreshSecrets,
        token_issuer: TokenIssuer,
        clock: Clock,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._unit_of_work = unit_of_work
        self._refresh_secrets = refresh_secrets
        self._token_issuer = token_issuer
        self._clock = clock

    def execute(self, data: RefreshSessionInput) -> IssuedTokens:
        now = self._clock()
        user_session, secret = self._open_session(data, now)
        if not self._refresh_secrets.matches(secret, user_session.refresh_token_hash):
            self._revoke_reused(user_session, now)
            raise InvalidRefreshTokenError

        user = self._users.get(user_session.user_id)
        if user is None or not user.is_active:
            raise InvalidRefreshTokenError

        new_secret = self._refresh_secrets.new_secret()
        user_session.rotate(self._refresh_secrets.hash(new_secret), now)
        self._sessions.save(user_session)
        self._unit_of_work.commit()
        return self._token_issuer.issue(user_session, new_secret, now)

    def _open_session(
        self, data: RefreshSessionInput, now: datetime
    ) -> tuple[UserSession, str]:
        """La sesión del token, abierta y del mismo canal, con su secreto."""
        if data.refresh_token is None:
            raise InvalidRefreshTokenError
        try:
            session_id, secret = parse_refresh_token(data.refresh_token)
        except TokenInvalidError as error:
            raise InvalidRefreshTokenError from error
        user_session = self._sessions.get_for_update(session_id)
        if user_session is None or not user_session.accepts(data.platform, now):
            raise InvalidRefreshTokenError
        return user_session, secret

    def _revoke_reused(self, user_session: UserSession, now: datetime) -> None:
        """El secreto ya se rotó: alguien usa un token viejo, quizá robado."""
        user_session.revoke(now)
        self._sessions.save(user_session)
        self._unit_of_work.commit()
