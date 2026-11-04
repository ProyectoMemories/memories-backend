"""Errores esperados de la API y su formato: {"code": ..., "message": ...}.

No importa FastAPI: los servicios lanzan estos errores y main.py los convierte
en respuestas HTTP.
"""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    code: str
    message: str


class FieldError(BaseModel):
    field: str
    message: str


class ValidationErrorResponse(ErrorResponse):
    errors: list[FieldError]


class AppError(Exception):
    """Error esperado: la app lo muestra al usuario según su `code`."""

    status_code = 400
    code = "bad_request"
    message = "La petición no es válida."

    def __init__(self, headers: dict[str, str] | None = None) -> None:
        super().__init__(self.message)
        self.headers = headers


class TooManyRequestsError(AppError):
    status_code = 429
    code = "too_many_requests"
    message = "Hiciste demasiados intentos. Espera un minuto y vuelve a probar."
