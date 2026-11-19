"""Caso de uso: iniciar sesión en un dispositivo (HU-03; RN-06, RN-67, D62-E)."""

from dataclasses import dataclass

from app.modules.auth.entities.errors import DeletionPeriodOverError
from app.modules.auth.entities.user import User
from app.modules.auth.entities.user_session import ClientPlatform, UserSession
from app.modules.auth.use_cases.errors import InvalidCredentialsError
from app.modules.auth.use_cases.ports import (
    PasswordHasher,
    RefreshSecrets,
    SessionGateway,
    UserGateway,
)
from app.modules.auth.use_cases.token_issuer import IssuedTokens, TokenIssuer
from app.shared.entities.clock import Clock
from app.shared.use_cases.ports import UnitOfWork


@dataclass(frozen=True)
class LogInInput:
    identifier: str
    password: str
    platform: ClientPlatform
    device_name: str | None


class LogIn:
    def __init__(
        self,
        users: UserGateway,
        sessions: SessionGateway,
        unit_of_work: UnitOfWork,
        hasher: PasswordHasher,
        refresh_secrets: RefreshSecrets,
        token_issuer: TokenIssuer,
        clock: Clock,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._unit_of_work = unit_of_work
        self._hasher = hasher
        self._refresh_secrets = refresh_secrets
        self._token_issuer = token_issuer
        self._clock = clock

    def execute(self, data: LogInInput) -> IssuedTokens:
        now = self._clock()
        user = self._user_with_password(data.identifier, data.password)
        # Desde aquí la contraseña es correcta: se puede decir por qué no entra.
        try:
            user.admit_login(now)
        except DeletionPeriodOverError as error:
            raise InvalidCredentialsError from error
        self._users.save(user)

        secret = self._refresh_secrets.new_secret()
        user_session = UserSession.open(
            user_id=user.id,
            platform=data.platform,
            device_name=data.device_name,
            refresh_token_hash=self._refresh_secrets.hash(secret),
            now=now,
        )
        self._sessions.add(user_session)
        self._unit_of_work.commit()
        return self._token_issuer.issue(user_session, secret, now)

    def _user_with_password(self, identifier: str, password: str) -> User:
        """El usuario si la contraseña coincide; el mismo error si no existe."""
        user = self._users.get_by_login(identifier)
        if user is None:
            self._hasher.verify_dummy(password)
            raise InvalidCredentialsError
        valid, new_hash = self._hasher.verify_and_update(password, user.password_hash)
        if not valid:
            raise InvalidCredentialsError
        if new_hash is not None:
            user.replace_password_hash(new_hash)  # RNF-08: parámetros al día
        return user
