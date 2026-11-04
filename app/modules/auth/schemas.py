"""Esquemas de entrada y salida de auth."""

import re
import uuid
from datetime import date
from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    StringConstraints,
)
from pydantic_core import PydanticCustomError

from app.modules.auth.models import AccountStatus, ClientPlatform

_USERNAME_CHARS = re.compile(r"^[A-Za-z0-9._]+$")


def _check_username(value: str) -> str:
    """RN-10 con mensajes que dicen qué está mal (la base lo vuelve a imponer)."""
    if not 3 <= len(value) <= 30:
        raise PydanticCustomError(
            "username_length", "Debe tener entre 3 y 30 caracteres."
        )
    if not _USERNAME_CHARS.match(value):
        raise PydanticCustomError(
            "username_chars", "Solo puede tener letras sin tilde, números, '.' y '_'."
        )
    if value.startswith(".") or value.endswith("."):
        raise PydanticCustomError(
            "username_dot_edges", "No puede empezar ni terminar con '.'."
        )
    if ".." in value:
        raise PydanticCustomError(
            "username_double_dot", "No puede tener dos '.' seguidos."
        )
    return value


Username = Annotated[str, AfterValidator(_check_username)]
Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]


class RegisterRequest(BaseModel):
    # Un campo desconocido, como is_superuser, se rechaza (D28).
    model_config = ConfigDict(extra="forbid")

    username: Username
    email: Annotated[EmailStr, Field(max_length=254)]
    # El largo de D62-B lo revisa el servicio; este tope solo evita textos enormes.
    password: Annotated[str, Field(max_length=1024)]
    first_name: Name
    paternal_surname: Name
    maternal_surname: Name | None = None
    birth_date: date
    accepts_privacy_policy: bool


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    status: AccountStatus


class VerifyEmailRequest(BaseModel):
    token: Annotated[str, Field(min_length=1, max_length=2048)]


class ResendVerificationRequest(BaseModel):
    email: Annotated[str, Field(min_length=1, max_length=254)]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Correo o nombre de usuario, sin importar mayúsculas (RN-06).
    identifier: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=254)
    ]
    password: Annotated[str, Field(min_length=1, max_length=1024)]
    platform: ClientPlatform
    device_name: Name | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"  # noqa: S105 (es el tipo, no un secreto)
    expires_in: int = Field(description="Segundos que dura el token de acceso.")
    refresh_token: str | None = Field(
        default=None,
        description="Solo en Android. En web viaja en una cookie httpOnly.",
    )


class RefreshTokenRequest(BaseModel):
    """Solo Android. En web el cuerpo va vacío y se usa la cookie."""

    model_config = ConfigDict(extra="forbid")

    refresh_token: Annotated[str, Field(min_length=1, max_length=200)]
