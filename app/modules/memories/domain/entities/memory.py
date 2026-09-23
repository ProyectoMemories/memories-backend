"""Entidad Recuerdo: la unidad central del producto (PRD, seccion 3).

Aqui viven las reglas que no pueden depender de la pantalla ni de la base de
datos:
  - un recuerdo sin fotografia no es un recuerdo;
  - no se puede recordar algo que todavia no ha pasado;
  - las fotografias son de quien crea el recuerdo.

Pendientes del PRD que se han fijado como supuestos y estan aislados aqui:
  - P16: el titulo y la fecha del momento son obligatorios.
  - P13: el maximo de fotografias es configurable (MAX_PHOTOS_PER_MEMORY).
  - P14: la ubicacion no forma parte del recuerdo todavia.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime

from app.modules.memories.domain.entities.photo import Photo
from app.modules.memories.domain.errors import (
    InvalidMemoryDescriptionError,
    InvalidMemoryTitleError,
    InvalidMomentDateError,
    MemoryNeedsAtLeastOnePhotoError,
    PhotoAlreadyAttachedError,
    PhotoNotFoundError,
    PhotoNotOwnedError,
    TooManyPhotosError,
)

MAX_TITLE_LENGTH = 120
MAX_DESCRIPTION_LENGTH = 2000


def _now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(slots=True)
class Memory:
    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    moment_date: date
    description: str | None = None
    photos: list[Photo] = field(default_factory=list)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    @classmethod
    def create(
        cls,
        *,
        owner_id: uuid.UUID,
        title: str,
        moment_date: date,
        photos: list[Photo],
        description: str | None = None,
        max_photos: int,
        today: date | None = None,
        memory_id: uuid.UUID | None = None,
    ) -> "Memory":
        memory = cls(
            id=memory_id or uuid.uuid4(),
            owner_id=owner_id,
            title=cls._validate_title(title),
            moment_date=cls._validate_moment_date(moment_date, today),
            description=cls._validate_description(description),
        )
        memory._assign_photos(photos, max_photos=max_photos, require_at_least_one=True)
        return memory

    @property
    def photo_count(self) -> int:
        return len(self.photos)

    def update_details(
        self,
        *,
        title: str | None = None,
        moment_date: date | None = None,
        description: str | None = None,
        clear_description: bool = False,
        today: date | None = None,
    ) -> None:
        if title is not None:
            self.title = self._validate_title(title)
        if moment_date is not None:
            self.moment_date = self._validate_moment_date(moment_date, today)
        if clear_description:
            self.description = None
        elif description is not None:
            self.description = self._validate_description(description)
        self.updated_at = _now()

    def add_photos(self, photos: list[Photo], *, max_photos: int) -> None:
        self._assign_photos(photos, max_photos=max_photos, require_at_least_one=False)
        self.updated_at = _now()

    def remove_photo(self, photo_id: uuid.UUID) -> Photo:
        photo = next((item for item in self.photos if item.id == photo_id), None)
        if photo is None:
            raise PhotoNotFoundError()
        if self.photo_count == 1:
            raise MemoryNeedsAtLeastOnePhotoError(
                "No se puede quitar la ultima fotografia: borra el recuerdo entero."
            )
        self.photos.remove(photo)
        photo.detach()
        self._reindex()
        self.updated_at = _now()
        return photo

    # ─── Reglas internas ────────────────────────────────────────────

    def _assign_photos(
        self, photos: list[Photo], *, max_photos: int, require_at_least_one: bool
    ) -> None:
        if require_at_least_one and not photos:
            raise MemoryNeedsAtLeastOnePhotoError()
        if not photos:
            return
        if self.photo_count + len(photos) > max_photos:
            raise TooManyPhotosError(f"Un recuerdo admite como maximo {max_photos} fotografias.")

        for photo in photos:
            if not photo.belongs_to(self.owner_id):
                raise PhotoNotOwnedError()
            if photo.is_attached and photo.memory_id != self.id:
                raise PhotoAlreadyAttachedError()
            self.photos.append(photo)

        self._reindex()

    def _reindex(self) -> None:
        for position, photo in enumerate(self.photos):
            photo.attach_to(self.id, position)

    @staticmethod
    def _validate_title(title: str) -> str:
        cleaned = title.strip()
        if not cleaned:
            raise InvalidMemoryTitleError("El recuerdo necesita un titulo.")
        if len(cleaned) > MAX_TITLE_LENGTH:
            raise InvalidMemoryTitleError(
                f"El titulo no puede pasar de {MAX_TITLE_LENGTH} caracteres."
            )
        return cleaned

    @staticmethod
    def _validate_description(description: str | None) -> str | None:
        if description is None:
            return None
        cleaned = description.strip()
        if not cleaned:
            return None
        if len(cleaned) > MAX_DESCRIPTION_LENGTH:
            raise InvalidMemoryDescriptionError(
                f"La descripcion no puede pasar de {MAX_DESCRIPTION_LENGTH} caracteres."
            )
        return cleaned

    @staticmethod
    def _validate_moment_date(moment_date: date, today: date | None) -> date:
        reference = today or datetime.now(tz=UTC).date()
        if moment_date > reference:
            raise InvalidMomentDateError("La fecha del recuerdo no puede estar en el futuro.")
        return moment_date
