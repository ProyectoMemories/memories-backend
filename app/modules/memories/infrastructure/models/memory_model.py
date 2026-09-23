"""Tabla memories."""

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db.base import Base
from app.shared.db.mixins import TimestampsMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:  # solo para los tipos: en ejecucion lo resuelve SQLAlchemy
    from app.modules.memories.infrastructure.models.photo_model import PhotoModel


class MemoryModel(UUIDPrimaryKeyMixin, TimestampsMixin, Base):
    __tablename__ = "memories"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    moment_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    photos: Mapped[list["PhotoModel"]] = relationship(
        "PhotoModel",
        back_populates="memory",
        order_by="PhotoModel.position",
        lazy="selectin",
    )

    __table_args__ = (
        # La lista y el calendario siempre consultan "mis recuerdos por fecha".
        Index("ix_memories_owner_id_moment_date", "owner_id", "moment_date"),
    )
