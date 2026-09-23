"""Esquemas HTTP del modulo de usuarios.

Pydantic vive aqui, en el borde. Ni el dominio ni los casos de uso lo conocen.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.users.domain.entities.user import User
from app.shared.pagination import Page
from app.shared.roles import UserRole


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

    @classmethod
    def from_entity(cls, user: User) -> "UserResponse":
        return cls(
            id=user.id,
            email=user.email.value,
            display_name=user.display_name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        )


class UpdateProfileRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=60, examples=["Victor"])


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def from_page(cls, page: Page[User]) -> "UserListResponse":
        return cls(
            items=[UserResponse.from_entity(user) for user in page.items],
            total=page.total,
            page=page.page,
            size=page.size,
            pages=page.pages,
        )
