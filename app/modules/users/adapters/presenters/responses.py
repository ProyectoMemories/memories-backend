"""Esquemas de salida de users."""

import uuid

from pydantic import BaseModel, Field


class ProfileResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    first_name: str
    paternal_surname: str
    maternal_surname: str | None = Field(
        description="null si la persona no lo escribió al registrarse."
    )
