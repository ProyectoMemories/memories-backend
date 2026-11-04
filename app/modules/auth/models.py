"""Modelos de app_user, privacy_consent y user_session (migración 0001)."""

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


class ClientPlatform(StrEnum):
    """Dónde se inició la sesión (D51, D56)."""

    ANDROID = "android"
    WEB = "web"


def _pg_enum(enum: type[StrEnum], name: str) -> Enum:
    # El tipo ya lo crea la migración; aquí solo se usa.
    return Enum(
        enum,
        name=name,
        create_type=False,
        values_callable=lambda members: [member.value for member in members],
    )


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
        _pg_enum(AccountStatus, "account_status")
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


class UserSession(Base):
    """Una sesión por dispositivo; guarda solo el hash del token de renovación."""

    __tablename__ = "user_session"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    refresh_token_hash: Mapped[str]
    platform: Mapped[ClientPlatform] = mapped_column(
        _pg_enum(ClientPlatform, "client_platform")
    )
    device_name: Mapped[str | None]
    created_at: Mapped[datetime]
    last_used_at: Mapped[datetime]
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
