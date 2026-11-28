"""Modelo ORM del perfil sobre app_user (migración 0001).

auth ya mapea app_user completa con su propio modelo. users no lo importa
(CLAUDE.md §7, D81): mapea solo las columnas del perfil, en una base
declarativa propia. Con la `Base` de shared, SQLAlchemy rechazaría dos clases
para la misma tabla en la misma MetaData.
"""

import uuid

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class UsersBase(DeclarativeBase):
    """Base de los modelos de users. Las tablas las crea la migración, no el ORM."""


class ProfileRecord(UsersBase):
    __tablename__ = "app_user"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    username: Mapped[str]
    email: Mapped[str]
    first_name: Mapped[str]
    paternal_surname: Mapped[str]
    maternal_surname: Mapped[str | None]
