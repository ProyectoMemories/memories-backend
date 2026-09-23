"""Esquemas HTTP de autenticacion."""

from pydantic import BaseModel, EmailStr, Field

from app.modules.auth.application.session import AuthenticatedSession
from app.modules.users.interfaces.http.schemas.user_schemas import UserResponse


class RegisterRequest(BaseModel):
    email: EmailStr = Field(examples=["victor@memories.app"])
    display_name: str = Field(min_length=1, max_length=60, examples=["Victor"])
    password: str = Field(min_length=8, max_length=72, examples=["unaClaveSegura1"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None
    all_devices: bool = False


class SessionResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 - es el tipo de esquema, no un secreto
    expires_in: int
    user: UserResponse

    @classmethod
    def from_session(cls, session: AuthenticatedSession) -> "SessionResponse":
        return cls(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            expires_in=session.access_token_expires_in,
            user=UserResponse.from_entity(session.user),
        )


class MessageResponse(BaseModel):
    message: str
