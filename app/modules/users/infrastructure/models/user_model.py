"""Tabla users.

Un archivo por tabla: es la leccion que nos dejo CRIS, donde todos los modelos
de un modulo compartian models.py y el archivo crecia sin freno.
"""

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.base import Base
from app.shared.db.mixins import TimestampsMixin, UUIDPrimaryKeyMixin
from app.shared.roles import UserRole


class UserModel(UUIDPrimaryKeyMixin, TimestampsMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(254), nullable=False, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(60), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            # Guarda "user"/"superuser" y no "USER"/"SUPERUSER".
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        default=UserRole.USER,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
