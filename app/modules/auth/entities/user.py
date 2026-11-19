"""Entidad User: la cuenta y sus estados (RN-11 a RN-14, RN-17, RN-68)."""

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum

from app.modules.auth.entities.errors import (
    AccountSuspendedError,
    DeletionPeriodOverError,
    EmailNotVerifiedError,
)
from app.shared.entities.ids import new_id

DELETION_GRACE_PERIOD = timedelta(days=30)  # RN-14


class AccountStatus(StrEnum):
    UNVERIFIED = "unverified"
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    PENDING_DELETION = "pending_deletion"
    SUSPENDED = "suspended"


@dataclass
class User:
    id: uuid.UUID
    username: str
    email: str
    password_hash: str
    first_name: str
    paternal_surname: str
    maternal_surname: str | None
    birth_date: date
    status: AccountStatus
    email_verified_at: datetime | None = None
    deletion_requested_at: datetime | None = None
    # La pone la base al crear la cuenta; cambia con cada contraseña nueva.
    password_changed_at: datetime | None = None

    @classmethod
    def register(
        cls,
        *,
        username: str,
        email: str,
        password_hash: str,
        first_name: str,
        paternal_surname: str,
        maternal_surname: str | None,
        birth_date: date,
    ) -> "User":
        """Toda cuenta nueva empieza sin verificar (RN-12)."""
        return cls(
            id=new_id(),
            username=username,
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            paternal_surname=paternal_surname,
            maternal_surname=maternal_surname,
            birth_date=birth_date,
            status=AccountStatus.UNVERIFIED,
        )

    @property
    def is_active(self) -> bool:
        return self.status is AccountStatus.ACTIVE

    @property
    def is_unverified(self) -> bool:
        return self.status is AccountStatus.UNVERIFIED

    @property
    def can_recover_password(self) -> bool:
        """Una cuenta suspendida no recibe el enlace: igual no puede entrar (RN-17)."""
        return self.status is not AccountStatus.SUSPENDED

    def verify_email(self, now: datetime) -> bool:
        """Activa la cuenta. Devuelve False si ya estaba verificada (HU-02)."""
        if not self.is_unverified:
            return False
        self.status = AccountStatus.ACTIVE
        self.email_verified_at = now
        return True

    def admit_login(self, now: datetime) -> None:
        """Deja entrar, reactivando si hace falta, o dice por qué no."""
        match self.status:
            case AccountStatus.UNVERIFIED:
                raise EmailNotVerifiedError  # RN-11
            case AccountStatus.SUSPENDED:
                raise AccountSuspendedError  # RN-17
            case AccountStatus.DEACTIVATED:
                self.status = AccountStatus.ACTIVE  # RN-68
            case AccountStatus.PENDING_DELETION:
                self._cancel_deletion(now)
            case AccountStatus.ACTIVE:
                pass

    def replace_password_hash(self, password_hash: str) -> None:
        """Mismo password con un hash al día (RNF-08): no cuenta como cambio."""
        self.password_hash = password_hash

    def change_password(self, password_hash: str, now: datetime) -> None:
        """Contraseña nueva: invalida los enlaces de recuperación anteriores (RN-19)."""
        self.password_hash = password_hash
        self.password_changed_at = now

    def _cancel_deletion(self, now: datetime) -> None:
        """Entrar dentro de los 30 días cancela la eliminación (RN-14)."""
        requested_at = self.deletion_requested_at
        if requested_at and now - requested_at >= DELETION_GRACE_PERIOD:
            raise DeletionPeriodOverError
        self.status = AccountStatus.ACTIVE
        self.deletion_requested_at = None
