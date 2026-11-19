"""Caso de uso: cerrar la sesión de este dispositivo (HU-05; D56)."""

from dataclasses import dataclass

from app.modules.auth.entities.user_session import ClientPlatform
from app.modules.auth.use_cases.ports import (
    RefreshSecrets,
    SessionGateway,
    TokenInvalidError,
)
from app.modules.auth.use_cases.refresh_token import parse_refresh_token
from app.shared.entities.clock import Clock
from app.shared.use_cases.ports import UnitOfWork


@dataclass(frozen=True)
class LogOutInput:
    refresh_token: str | None
    platform: ClientPlatform


class LogOut:
    def __init__(
        self,
        sessions: SessionGateway,
        unit_of_work: UnitOfWork,
        refresh_secrets: RefreshSecrets,
        clock: Clock,
    ) -> None:
        self._sessions = sessions
        self._unit_of_work = unit_of_work
        self._refresh_secrets = refresh_secrets
        self._clock = clock

    def execute(self, data: LogOutInput) -> None:
        """Revoca la sesión si el token es válido. Repetirlo no da error."""
        if data.refresh_token is None:
            return
        try:
            session_id, secret = parse_refresh_token(data.refresh_token)
        except TokenInvalidError:
            return  # No hay sesión que cerrar: el cliente igual borra sus tokens.

        now = self._clock()
        user_session = self._sessions.get_for_update(session_id)
        if (
            user_session is not None
            and user_session.accepts(data.platform, now)
            and self._refresh_secrets.matches(secret, user_session.refresh_token_hash)
        ):
            user_session.revoke(now)
            self._sessions.save(user_session)
            self._unit_of_work.commit()
