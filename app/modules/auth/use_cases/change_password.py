"""Caso de uso: cambiar la contraseña con la sesión abierta (HU-07; RN-67)."""

import uuid
from dataclasses import dataclass

from app.modules.auth.entities.password_policy import PasswordPolicy
from app.modules.auth.use_cases.errors import (
    CurrentPasswordIncorrectError,
    NotAuthenticatedError,
)
from app.modules.auth.use_cases.ports import (
    PasswordHasher,
    SessionGateway,
    UserGateway,
)
from app.shared.entities.clock import Clock
from app.shared.use_cases.ports import UnitOfWork


@dataclass(frozen=True)
class ChangePasswordInput:
    user_id: uuid.UUID
    current_password: str
    new_password: str


class ChangePassword:
    def __init__(
        self,
        users: UserGateway,
        sessions: SessionGateway,
        unit_of_work: UnitOfWork,
        hasher: PasswordHasher,
        password_policy: PasswordPolicy,
        clock: Clock,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._unit_of_work = unit_of_work
        self._hasher = hasher
        self._password_policy = password_policy
        self._clock = clock

    def execute(self, data: ChangePasswordInput) -> None:
        """Guarda la nueva y cierra todas las sesiones, también la actual."""
        user = self._users.get(data.user_id)
        if user is None:
            raise NotAuthenticatedError
        valid, _ = self._hasher.verify_and_update(
            data.current_password, user.password_hash
        )
        if not valid:
            raise CurrentPasswordIncorrectError
        self._password_policy.ensure_acceptable(data.new_password)

        now = self._clock()
        user.change_password(self._hasher.hash(data.new_password), now)
        self._users.save(user)
        self._sessions.revoke_all(user.id, now)
        self._unit_of_work.commit()
