"""Punto de entrada de la API de Memories.

Monolito modular: una sola aplicacion, un modulo por capacidad del producto.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import text

from app.api import api_router
from app.config.database import engine
from app.config.settings import get_settings
from app.core.cache.factory import get_cache
from app.core.logging import configure_logging
from app.core.middleware import RequestIDMiddleware, register_error_handlers

settings = get_settings()
logger = structlog.get_logger(__name__)

HOSTS_LOCALES = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",  # noqa: S104 - es un host que se compara, no una direccion de escucha
    "::1",
    "[::1]",
    "host.docker.internal",
}


def _peticion_es_local(request: Request) -> bool:
    host = (request.headers.get("host") or request.url.hostname or "").strip().lower()
    # Se quita el puerto: "localhost:8000" es tan local como "localhost".
    sin_puerto = host.split("]")[0] + "]" if host.startswith("[") else host.split(":")[0]
    return sin_puerto in HOSTS_LOCALES


def _exigir_documentacion_local(request: Request) -> None:
    """La documentacion no se publica fuera de local.

    Se responde 404 y no 403: un 403 confirmaria que ahi hay algo.
    """
    if not settings.DOCS_LOCAL_ONLY or _peticion_es_local(request):
        return
    raise HTTPException(status_code=404, detail="Not Found")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging(settings)
    logger.info(
        "api_arrancando",
        env=settings.ENV,
        storage=settings.STORAGE_PROVIDER,
        cache=settings.CACHE_PROVIDER,
        hashing=settings.PASSWORD_HASHING_SCHEME,
    )
    yield
    await get_cache().close()
    await engine.dispose()
    logger.info("api_detenida")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "API de Memories: guardar y revivir recuerdos.\n\n"
            "Modulos: **auth** (sesiones), **users** (perfil), "
            "**photos** (subida de imagenes) y **memories** (recuerdos, "
            "calendario y revivir)."
        ),
        lifespan=lifespan,
        # Las tres rutas se sirven a mano para poder cerrarlas fuera de local.
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    register_error_handlers(app)
    app.include_router(api_router, prefix=settings.API_PREFIX)

    @app.get("/health", tags=["Salud"], summary="Comprobacion de vida")
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": settings.APP_VERSION}

    @app.get("/health/ready", tags=["Salud"], summary="Comprobacion de dependencias")
    async def health_ready() -> JSONResponse:
        checks: dict[str, Any] = {}
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            checks["database"] = "ok"
        except Exception as exc:  # noqa: BLE001 - el diagnostico es la respuesta
            checks["database"] = f"error: {exc}"

        checks["cache"] = "ok" if await get_cache().ping() else "error"

        todo_ok = all(value == "ok" for value in checks.values())
        return JSONResponse(
            status_code=200 if todo_ok else 503,
            content={"status": "ok" if todo_ok else "degraded", "checks": checks},
        )

    @app.get("/openapi.json", include_in_schema=False)
    async def openapi_schema(request: Request) -> JSONResponse:
        _exigir_documentacion_local(request)
        return JSONResponse(app.openapi())

    @app.get("/docs", include_in_schema=False)
    async def swagger_ui(request: Request) -> HTMLResponse:
        _exigir_documentacion_local(request)
        return get_swagger_ui_html(openapi_url="/openapi.json", title=f"{app.title} - Swagger")

    @app.get("/redoc", include_in_schema=False)
    async def redoc_ui(request: Request) -> HTMLResponse:
        _exigir_documentacion_local(request)
        return get_redoc_html(openapi_url="/openapi.json", title=f"{app.title} - ReDoc")

    return app


app = create_app()
