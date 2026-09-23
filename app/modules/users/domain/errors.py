"""Errores del dominio de usuarios."""

from app.shared.errors import ConflictError, NotFoundError, ValidationError


class UserNotFoundError(NotFoundError):
    code = "user_not_found"

    def __init__(self, message: str = "El usuario no existe.") -> None:
        super().__init__(message)


class EmailAlreadyRegisteredError(ConflictError):
    code = "email_already_registered"

    def __init__(self, message: str = "Ese correo ya tiene una cuenta.") -> None:
        super().__init__(message)


class InvalidEmailError(ValidationError):
    code = "invalid_email"


class WeakPasswordError(ValidationError):
    code = "weak_password"


class InvalidDisplayNameError(ValidationError):
    code = "invalid_display_name"
