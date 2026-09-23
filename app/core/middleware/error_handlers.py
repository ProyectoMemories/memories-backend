"""Traduccion de errores a respuestas HTTP.

El dominio lanza errores de negocio sin saber nada de HTTP; aqui se decide que
codigo le corresponde a cada uno. Todas las respuestas de error tienen la misma
forma, para que el cliente Flutter las trate en un solo sitio.
"""

from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.shared.errors import (
    AppError,
    AuthenticationError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitExceededError,
    StorageError,
    ValidationError,
)

logger = structlog.get_logger(__name__)

STATUS_BY_ERROR: dict[type[AppError], int] = {
    ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    RateLimitExceededError: status.HTTP_429_TOO_MANY_REQUESTS,
    StorageError: status.HTTP_502_BAD_GATEWAY,
}


def _payload(
    code: str, message: str, request: Request, details: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "request_id": getattr(request.state, "request_id", None),
        }
    }


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        status_code = status.HTTP_400_BAD_REQUEST
        for error_type, mapped in STATUS_BY_ERROR.items():
            if isinstance(exc, error_type):
                status_code = mapped
                break
        if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
            logger.error("error_de_aplicacion", code=exc.code, message=exc.message)
        return JSONResponse(
            status_code=status_code,
            content=_payload(exc.code, exc.message, request, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_payload(
                "invalid_request",
                "Los datos enviados no son validos.",
                request,
                {"fields": [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]},
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        # Nunca se filtra el detalle interno al cliente: va al log.
        logger.exception("error_no_controlado", error=str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_payload("internal_error", "Ocurrio un error inesperado.", request),
        )
