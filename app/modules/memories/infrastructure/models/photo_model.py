"""Tabla photos."""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.db.base import Base
from app.shared.db.mixins import TimestampsMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:  # solo para los tipos: en ejecucion lo resuelve SQLAlchemy
    from app.modules.memories.infrastructure.models.memory_model import MemoryModel


class PhotoModel(UUIDPrimaryKeyMixin, TimestampsMixin, Base):
    __tablename__ = "photos"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Nula mientras la fotografia esta subida pero todavia sin recuerdo.
    memory_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("memories.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    memory: Mapped["MemoryModel | None"] = relationship("MemoryModel", back_populates="photos")
