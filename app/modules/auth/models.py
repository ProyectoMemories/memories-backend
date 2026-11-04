"""Modelos de app_user y privacy_consent, alineados con la migración 0001."""

import uuid
from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import Enum, FetchedValue, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AccountStatus(StrEnum):
    """Estados de la cuenta (RN-12)."""

    UNVERIFIED = "unverified"
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    PENDING_DELETION = "pending_deletion"
    SUSPENDED = "suspended"


class AppUser(Base):
    __tablename__ = "app_user"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    username: Mapped[str]
    email: Mapped[str]
    password_hash: Mapped[str]
    first_name: Mapped[str]
    paternal_surname: Mapped[str]
    maternal_surname: Mapped[str | None]
    birth_date: Mapped[date]
    status: Mapped[AccountStatus] = mapped_column(
        # El tipo ya lo crea la migración; aquí solo se usa.
        Enum(
            AccountStatus,
            name="account_status",
            create_type=False,
            values_callable=lambda statuses: [status.value for status in statuses],
        )
    )
    # FetchedValue: los pone la base (DEFAULT o trigger), no el ORM.
    is_superuser: Mapped[bool] = mapped_column(server_default=FetchedValue())
    email_verified_at: Mapped[datetime | None]
    password_changed_at: Mapped[datetime] = mapped_column(server_default=FetchedValue())
    suspended_at: Mapped[datetime | None]
    deletion_requested_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=FetchedValue())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=FetchedValue(), server_onupdate=FetchedValue()
    )


class PrivacyConsent(Base):
    """Qué versión de la política aceptó cada usuario y cuándo (RN-50)."""

    __tablename__ = "privacy_consent"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    policy_version: Mapped[str]
    accepted_at: Mapped[datetime]
