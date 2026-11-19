"""Presenta la cuenta recién creada."""

from app.modules.auth.adapters.presenters.responses import UserResponse
from app.modules.auth.use_cases.register_user import RegisteredUser


def present_registered_user(registered: RegisteredUser) -> UserResponse:
    return UserResponse(
        id=registered.id,
        username=registered.username,
        email=registered.email,
        status=registered.status,
    )
