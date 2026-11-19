"""Presenta los errores como respuestas HTTP con el formato {code, message}.

Aquí, y solo aquí, cada categoría de error se convierte en un código HTTP.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.shared.entities.errors import (
    AppError,
    BusinessRuleError,
    ConflictError,
    ForbiddenError,
    InvalidRequestError,
    NotFoundError,
    TooManyRequestsError,
    UnauthorizedError,
)

_STATUS_BY_CATEGORY: dict[type[AppError], int] = {
    InvalidRequestError: 400,
    UnauthorizedError: 401,
    ForbiddenError: 403,
    NotFoundError: 404,
    ConflictError: 409,
    BusinessRuleError: 422,
    TooManyRequestsError: 429,
}


class ErrorResponse(BaseModel):
    code: str
    message: str


class FieldError(BaseModel):
    field: str
    message: str


class ValidationErrorResponse(ErrorResponse):
    errors: list[FieldError]


def status_for(error: AppError) -> int:
    for category in type(error).__mro__:
        if category in _STATUS_BY_CATEGORY:
            return _STATUS_BY_CATEGORY[category]
    # Un AppError sin categoría es un error de programación, no del usuario.
    return 500


def headers_for(error: AppError) -> dict[str, str] | None:
    if isinstance(error, UnauthorizedError):
        return {"WWW-Authenticate": "Bearer"}
    if isinstance(error, TooManyRequestsError):
        return {"Retry-After": str(error.retry_after_seconds)}
    return None


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_error)  # type: ignore[arg-type]


def _app_error(_: Request, error: AppError) -> JSONResponse:
    body = ErrorResponse(code=error.code, message=error.message)
    return JSONResponse(
        body.model_dump(), status_code=status_for(error), headers=headers_for(error)
    )


def _validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
    errors = [
        FieldError(
            # loc es ("body", "campo", ...): se quita "body".
            field=".".join(str(part) for part in item["loc"][1:]),
            message=item["msg"],
        )
        for item in error.errors()
    ]
    body = ValidationErrorResponse(
        code="validation_error", message="Hay datos inválidos.", errors=errors
    )
    return JSONResponse(body.model_dump(), status_code=422)
