"""Motor y sesiones de SQLAlchemy (asincronas)."""

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config.settings import get_settings

settings = get_settings()

_engine_options: dict[str, Any] = {
    "pool_pre_ping": True,
    "echo": settings.DEBUG and settings.ENV == "development",
}

if settings.ENV == "testing":
    # Cada test corre en su propio event loop. Una conexion del pool creada en
    # un loop y reutilizada en otro rompe asyncpg, asi que en pruebas no se
    # reutilizan conexiones.
    _engine_options["poolclass"] = NullPool
else:
    _engine_options.update(
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    )

engine: AsyncEngine = create_async_engine(settings.DATABASE_URL, **_engine_options)

session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Una sesion por peticion: confirma al terminar bien, revierte si falla.

    Los casos de uso no hacen commit; la unidad de trabajo es la peticion HTTP.
    """
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
