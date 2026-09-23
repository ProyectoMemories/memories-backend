"""Entidad Usuario.

Python puro: ni ORM, ni Pydantic, ni FastAPI. Se puede instanciar y probar sin
base de datos.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.modules.users.domain.errors import InvalidDisplayNameError
from app.modules.users.domain.value_objects.email import Email
from app.shared.roles import UserRole

MAX_DISPLAY_NAME_LENGTH = 60


def _now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(slots=True)
class User:
    id: uuid.UUID
    email: Email
    display_name: str
    password_hash: str
    role: UserRole = UserRole.USER
    is_active: bool = True
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    @classmethod
    def register(
        cls,
        *,
        email: Email,
        display_name: str,
        password_hash: str,
        role: UserRole = UserRole.USER,
        user_id: uuid.UUID | None = None,
    ) -> "User":
        return cls(
            id=user_id or uuid.uuid4(),
            email=email,
            display_name=cls._validate_display_name(display_name),
            password_hash=password_hash,
            role=role,
        )

    def rename(self, display_name: str) -> None:
        self.display_name = self._validate_display_name(display_name)
        self.updated_at = _now()

    def change_password_hash(self, password_hash: str) -> None:
        self.password_hash = password_hash
        self.updated_at = _now()

    def deactivate(self) -> None:
        self.is_active = False
        self.updated_at = _now()

    def activate(self) -> None:
        self.is_active = True
        self.updated_at = _now()

    @staticmethod
    def _validate_display_name(display_name: str) -> str:
        cleaned = display_name.strip()
        if not cleaned:
            raise InvalidDisplayNameError("El nombre es obligatorio.")
        if len(cleaned) > MAX_DISPLAY_NAME_LENGTH:
            raise InvalidDisplayNameError(
                f"El nombre no puede pasar de {MAX_DISPLAY_NAME_LENGTH} caracteres."
            )
        return cleaned
