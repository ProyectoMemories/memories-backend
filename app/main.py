"""Raíz de composición de la API (círculo Frameworks & Drivers).

Arma FastAPI, crea los adaptadores compartidos y monta cada módulo. Se usa una
fábrica (`create_app`) para que las pruebas armen la app con su propia
configuración. Uvicorn la llama con `--factory`.
"""

from collections.abc import Iterator
from typing import Literal

from fastapi import BackgroundTasks, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.modules.auth.adapters.controllers.router import router as auth_router
from app.modules.auth.frameworks.composition import AuthModule
from app.shared.adapters.deferred_email_sender import DeferredEmailSender
from app.shared.adapters.error_presenter import register_error_handlers
from app.shared.adapters.rate_limit import RateLimiter
from app.shared.adapters.smtp_email_sender import SmtpEmailSender
from app.shared.frameworks.config import Settings, get_settings
from app.shared.frameworks.database import create_sessionmaker
from app.shared.use_cases.ports import EmailSender


class HealthResponse(BaseModel):
    status: Literal["ok"]


def open_request_scope(
    request: Request, background_tasks: BackgroundTasks
) -> Iterator[None]:
    """Una sesión de base por petición y los interactores que la usan.

    Lo que no se confirmó con commit se descarta al cerrar la sesión. Los
    correos diferidos se envían cuando la respuesta ya salió (D74); si no hay
    ninguno, `flush` no hace nada.
    """
    state = request.app.state
    deferred_email = DeferredEmailSender(state.email_sender)
    background_tasks.add_task(deferred_email.flush)
    with state.sessionmaker() as session:
        request.state.auth = state.auth_module.use_cases(session, deferred_email)
        yield


def create_app(
    settings: Settings | None = None, email_sender: EmailSender | None = None
) -> FastAPI:
    settings = settings or get_settings()
    email_sender = email_sender or SmtpEmailSender(
        settings.smtp_host, settings.smtp_port, settings.email_from
    )

    app = FastAPI(
        title="Memories API",
        version="0.1.0",
        # scope="function": la sesión se cierra antes de enviar la respuesta,
        # así un SMTP lento en segundo plano no retiene una conexión (D74).
        dependencies=[Depends(open_request_scope, scope="function")],
    )
    app.state.settings = settings
    app.state.sessionmaker = create_sessionmaker(settings.database_url)
    app.state.rate_limiter = RateLimiter()
    app.state.email_sender = email_sender
    app.state.auth_module = AuthModule(settings, email_sender)

    _add_cors(app, settings)
    register_error_handlers(app)
    _add_health(app)
    app.include_router(auth_router)
    return app


def _add_cors(app: FastAPI, settings: Settings) -> None:
    # La cookie de renovación viaja con credenciales, por eso solo se acepta el
    # origen de la app web (D56, CLAUDE.md §9).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_app_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )


def _add_health(app: FastAPI) -> None:
    @app.get("/health", tags=["health"])
    def health() -> HealthResponse:
        """Responde si el proceso de la API está vivo."""
        return HealthResponse(status="ok")
