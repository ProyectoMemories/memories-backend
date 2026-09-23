"""Esquemas HTTP de recuerdos."""

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from app.modules.memories.application.use_cases.get_memory_calendar import CalendarDay
from app.modules.memories.domain.entities.memory import (
    MAX_DESCRIPTION_LENGTH,
    MAX_TITLE_LENGTH,
    Memory,
)
from app.modules.memories.interfaces.http.schemas.photo_schemas import PhotoResponse


class CreateMemoryRequest(BaseModel):
    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    moment_date: date
    photo_ids: list[uuid.UUID] = Field(min_length=1)
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)


class UpdateMemoryRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=MAX_TITLE_LENGTH)
    moment_date: date | None = None
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    # Distingue "no toques la descripcion" (None) de "borrala" (true).
    clear_description: bool = False


class MemoryResponse(BaseModel):
    id: uuid.UUID
    title: str
    moment_date: date
    description: str | None
    photos: list[PhotoResponse]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, memory: Memory, photos: list[PhotoResponse]) -> "MemoryResponse":
        return cls(
            id=memory.id,
            title=memory.title,
            moment_date=memory.moment_date,
            description=memory.description,
            photos=photos,
            created_at=memory.created_at,
            updated_at=memory.updated_at,
        )


class MemoryListResponse(BaseModel):
    items: list[MemoryResponse]
    total: int
    page: int
    size: int
    pages: int


class CalendarDayResponse(BaseModel):
    day: date
    count: int

    @classmethod
    def from_entity(cls, calendar_day: CalendarDay) -> "CalendarDayResponse":
        return cls(day=calendar_day.day, count=calendar_day.count)


class CalendarResponse(BaseModel):
    year: int
    month: int
    days: list[CalendarDayResponse]


class ReviveResponse(BaseModel):
    reason: str
    memories: list[MemoryResponse]
