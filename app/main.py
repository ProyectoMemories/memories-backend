"""Punto de entrada de la API.

Se usa una fábrica (`create_app`) para que las pruebas armen la app con su
propia configuración, sin depender de variables de entorno.
Uvicorn la llama con `--factory`.
"""

from typing import Literal

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.db import create_sessionmaker
from app.email import EmailSender, SmtpEmailSender
from app.errors import AppError, ErrorResponse, FieldError, ValidationErrorResponse
from app.modules.auth.passwords import PasswordHasher
from app.modules.auth.router import router as auth_router
from app.rate_limit import RateLimiter


class HealthResponse(BaseModel):
    status: Literal["ok"]


def create_app(
    settings: Settings | None = None, email_sender: EmailSender | None = None
) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(title="Memories API", version="0.1.0")
    app.state.settings = settings
    app.state.sessionmaker = create_sessionmaker(settings.database_url)
    app.state.email_sender = email_sender or SmtpEmailSender(
        settings.smtp_host, settings.smtp_port, settings.email_from
    )
    app.state.password_hasher = PasswordHasher()
    app.state.rate_limiter = RateLimiter()

    # La cookie de renovación viaja con credenciales, por eso solo se acepta el
    # origen de la app web (D56, CLAUDE.md §9).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_app_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    _register_error_handlers(app)

    @app.get("/health", tags=["health"])
    def health() -> HealthResponse:
        """Responde si el proceso de la API está vivo."""
        return HealthResponse(status="ok")

    app.include_router(auth_router)
    return app


def _register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    def _app_error(_: Request, error: AppError) -> JSONResponse:
        body = ErrorResponse(code=error.code, message=error.message)
        return JSONResponse(
            body.model_dump(), status_code=error.status_code, headers=error.headers
        )

    @app.exception_handler(RequestValidationError)
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
