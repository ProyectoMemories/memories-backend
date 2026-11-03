"""Punto de entrada de la API.

Se usa una fábrica (`create_app`) para que las pruebas armen la app con su
propia configuración, sin depender de variables de entorno.
Uvicorn la llama con `--factory`.
"""

from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import Settings, get_settings


class HealthResponse(BaseModel):
    status: Literal["ok"]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    app = FastAPI(title="Memories API", version="0.1.0")
    app.state.settings = settings

    # La cookie de renovación viaja con credenciales, por eso solo se acepta el
    # origen de la app web (D56, CLAUDE.md §9).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.web_app_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/health", tags=["health"])
    def health() -> HealthResponse:
        """Responde si el proceso de la API está vivo."""
        return HealthResponse(status="ok")

    return app
