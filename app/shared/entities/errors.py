"""Errores de negocio y sus categorías.

Cada error de negocio hereda de una categoría que dice qué clase de problema
es. `shared/adapters/error_presenter.py` traduce la categoría a un código HTTP:
el dominio nunca conoce HTTP (CLAUDE.md §7).
"""


class AppError(Exception):
    """Error esperado: la app lo muestra al usuario según su `code`."""

    code = "app_error"
    message = "Ocurrió un error."

    def __init__(self) -> None:
        super().__init__(self.message)


class InvalidRequestError(AppError):
    """La petición no se puede cumplir tal como viene (por ejemplo, un enlace roto)."""


class UnauthorizedError(AppError):
    """Falta identificarse o la identidad no es válida."""


class ForbiddenError(AppError):
    """Se sabe quién es, pero no puede hacer esto."""


class NotFoundError(AppError):
    """No existe, o es ajeno: se responde igual para no revelarlo (D60)."""


class ConflictError(AppError):
    """Choca con datos que ya existen."""


class BusinessRuleError(AppError):
    """Los datos tienen buen formato pero incumplen una regla de negocio."""


class TooManyRequestsError(AppError):
    code = "too_many_requests"
    message = "Hiciste demasiados intentos. Espera un minuto y vuelve a probar."

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__()
        self.retry_after_seconds = retry_after_seconds
