"""Caso de uso: recuerdos agrupados por dia (capacidad CP-08, vista calendario).

Devuelve solo cuantos hay en cada dia: pintar el calendario no necesita el
contenido de cada recuerdo, y traerlo entero seria mover datos para nada.
"""

import uuid
from dataclasses import dataclass
from datetime import date

from app.modules.memories.domain.repositories.memory_repository import MemoryRepository
from app.shared.errors import ValidationError


@dataclass(frozen=True, slots=True)
class CalendarDay:
    day: date
    count: int


class GetMemoryCalendar:
    def __init__(self, memories: MemoryRepository) -> None:
        self._memories = memories

    async def execute(self, owner_id: uuid.UUID, year: int, month: int) -> list[CalendarDay]:
        if not 1 <= month <= 12:
            raise ValidationError("El mes debe estar entre 1 y 12.")
        if not 1900 <= year <= 2999:
            raise ValidationError("El ano no es valido.")

        counts = await self._memories.count_by_day(owner_id, year, month)
        return [CalendarDay(day=day, count=count) for day, count in sorted(counts.items())]
