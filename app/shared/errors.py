"""Errores compartidos por todas las capas.

Este modulo es deliberadamente puro: no importa FastAPI, SQLAlchemy ni nada
de infraestructura, para que el dominio pueda usarlo sin romper la regla de
dependencia. La traduccion a codigos HTTP vive en
`app/core/middleware/error_handlers.py`.
"""

from typing import Any


class AppError(Exception):
    """Raiz de todos los errores propios."""

    code = "app_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(AppError):
    """La entrada no cumple una regla de negocio."""

    code = "validation_error"


class NotFoundError(AppError):
    """El recurso no existe, o no pertenece a quien lo pide."""

    code = "not_found"


class ConflictError(AppError):
    """La operacion choca con el estado actual (duplicados, por ejemplo)."""

    code = "conflict"


class AuthenticationError(AppError):
    """Credenciales ausentes, invalidas o vencidas."""

    code = "authentication_error"


class PermissionDeniedError(AppError):
    """Autenticado, pero sin permiso para esta operacion."""

    code = "permission_denied"


class RateLimitExceededError(AppError):
    """Demasiadas peticiones en poco tiempo."""

    code = "rate_limit_exceeded"


class StorageError(AppError):
    """Fallo hablando con el almacenamiento de archivos."""

    code = "storage_error"
