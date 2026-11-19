"""Errores de negocio de las cuentas."""

from app.shared.entities.errors import ConflictError, ForbiddenError


class UsernameTakenError(ConflictError):
    code = "username_taken"
    message = "Ese nombre de usuario ya está en uso."


class EmailTakenError(ConflictError):
    code = "email_taken"
    message = "Ya existe una cuenta con ese correo."


class EmailNotVerifiedError(ForbiddenError):
    code = "email_not_verified"
    message = "Verifica tu correo para entrar. Puedes pedir otro enlace."


class AccountSuspendedError(ForbiddenError):
    code = "account_suspended"
    message = "Tu cuenta está suspendida."


class DeletionPeriodOverError(Exception):
    """Pasaron los 30 días de la eliminación (RN-14); solo falta la purga diaria.

    No es un AppError: al usuario se le responde como a una cuenta inexistente.
    """
