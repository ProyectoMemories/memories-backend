"""Errores del dominio de recuerdos."""

from app.shared.errors import ConflictError, NotFoundError, ValidationError


class MemoryNotFoundError(NotFoundError):
    code = "memory_not_found"

    def __init__(self, message: str = "El recuerdo no existe.") -> None:
        super().__init__(message)


class PhotoNotFoundError(NotFoundError):
    code = "photo_not_found"

    def __init__(self, message: str = "La fotografia no existe.") -> None:
        super().__init__(message)


class InvalidMemoryTitleError(ValidationError):
    code = "invalid_memory_title"


class InvalidMemoryDescriptionError(ValidationError):
    code = "invalid_memory_description"


class InvalidMomentDateError(ValidationError):
    code = "invalid_moment_date"


class MemoryNeedsAtLeastOnePhotoError(ValidationError):
    code = "memory_needs_photo"

    def __init__(self, message: str = "Un recuerdo necesita al menos una fotografia.") -> None:
        super().__init__(message)


class TooManyPhotosError(ValidationError):
    code = "too_many_photos"


class PhotoAlreadyAttachedError(ConflictError):
    code = "photo_already_attached"

    def __init__(self, message: str = "Esa fotografia ya pertenece a otro recuerdo.") -> None:
        super().__init__(message)


class PhotoNotOwnedError(ValidationError):
    code = "photo_not_owned"

    def __init__(
        self, message: str = "Alguna fotografia no pertenece a quien crea el recuerdo."
    ) -> None:
        super().__init__(message)


class InvalidImageError(ValidationError):
    code = "invalid_image"
