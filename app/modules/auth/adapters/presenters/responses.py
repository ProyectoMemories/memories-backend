"""Esquemas de salida de auth."""

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.modules.auth.entities.user import AccountStatus


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    status: AccountStatus


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 (es el tipo, no un secreto)
    expires_in: int = Field(description="Segundos que dura el token de acceso.")
    refresh_token: str | None = Field(
        default=None,
        description="Solo en Android. En web viaja en una cookie httpOnly.",
    )
