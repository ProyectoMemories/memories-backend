"""Entidad UserSession: una sesión por dispositivo (D56, RN-67)."""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.shared.entities.ids import new_id

SESSION_LIFETIME = timedelta(days=30)


class ClientPlatform(StrEnum):
    """Dónde se inició la sesión (D51)."""

    ANDROID = "android"
    WEB = "web"


@dataclass
class UserSession:
    id: uuid.UUID
    user_id: uuid.UUID
    refresh_token_hash: str
    platform: ClientPlatform
    device_name: str | None
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    revoked_at: datetime | None = None

    @classmethod
    def open(
        cls,
        *,
        user_id: uuid.UUID,
        platform: ClientPlatform,
        device_name: str | None,
        refresh_token_hash: str,
        now: datetime,
    ) -> "UserSession":
        return cls(
            id=new_id(),
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            platform=platform,
            device_name=device_name,
            created_at=now,
            last_used_at=now,
            expires_at=now + SESSION_LIFETIME,
        )

    def is_open(self, now: datetime) -> bool:
        """Ni revocada ni vencida."""
        return self.revoked_at is None and self.expires_at > now

    def accepts(self, platform: ClientPlatform, now: datetime) -> bool:
        """Abierta y usada por el mismo canal en que se abrió."""
        return self.is_open(now) and self.platform is platform

    def belongs_to(self, user_id: uuid.UUID) -> bool:
        return self.user_id == user_id

    def rotate(self, refresh_token_hash: str, now: datetime) -> None:
        """Nuevo token de renovación y 30 días más de vida."""
        self.refresh_token_hash = refresh_token_hash
        self.last_used_at = now
        self.expires_at = now + SESSION_LIFETIME

    def revoke(self, now: datetime) -> None:
        self.revoked_at = now
