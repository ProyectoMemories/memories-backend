"""Caso de uso: crear una contraseña nueva con el enlace (HU-06; RN-19, RN-67)."""

from dataclasses import dataclass

from app.modules.auth.entities.password_policy import PasswordPolicy
from app.modules.auth.entities.user import User
from app.modules.auth.use_cases.errors import ExpiredLinkError, InvalidLinkError
from app.modules.auth.use_cases.ports import (
    PasswordHasher,
    PasswordResetTokens,
    SessionGateway,
    TokenExpiredError,
    TokenInvalidError,
    UserGateway,
)
from app.shared.entities.clock import Clock
from app.shared.use_cases.ports import UnitOfWork


@dataclass(frozen=True)
class ResetPasswordInput:
    token: str
    new_password: str


class ResetPassword:
    def __init__(
        self,
        users: UserGateway,
        sessions: SessionGateway,
        unit_of_work: UnitOfWork,
        hasher: PasswordHasher,
        password_policy: PasswordPolicy,
        reset_tokens: PasswordResetTokens,
        clock: Clock,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._unit_of_work = unit_of_work
        self._hasher = hasher
        self._password_policy = password_policy
        self._reset_tokens = reset_tokens
        self._clock = clock

    def execute(self, data: ResetPasswordInput) -> None:
        user = self._user_from_link(data.token)
        self._password_policy.ensure_acceptable(data.new_password)

        now = self._clock()
        user.change_password(self._hasher.hash(data.new_password), now)
        self._users.save(user)
        self._sessions.revoke_all(user.id, now)
        self._unit_of_work.commit()

    def _user_from_link(self, token: str) -> User:
        """El usuario del enlace, si sigue vigente y nadie lo usó todavía."""
        try:
            user_id, password_changed_at = self._reset_tokens.read(token)
        except TokenExpiredError as error:
            raise ExpiredLinkError from error
        except TokenInvalidError as error:
            raise InvalidLinkError from error

        user = self._users.get(user_id)
        # Si la contraseña cambió después de pedir el enlace (incluso con este
        # mismo enlace), la fecha ya no coincide: es un enlace usado (RN-19).
        if user is None or user.password_changed_at != password_changed_at:
            raise InvalidLinkError
        return user
