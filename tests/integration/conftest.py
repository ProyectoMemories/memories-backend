"""Fixtures de las pruebas que hablan con la base de datos.

El esquema se crea una vez por sesion y se borra al terminar. Entre test y test
se vacian las tablas, de modo que cada uno empieza en limpio.
"""

import asyncio
import shutil
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from app.config.database import engine
from app.config.settings import get_settings
from app.main import create_app
from app.shared.db.registry import Base

settings = get_settings()
TABLES = ("photos", "memories", "users")


async def _crear_esquema() -> None:
    motor = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    async with motor.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.DB_SCHEMA}"'))
        await connection.run_sync(Base.metadata.create_all)
    await motor.dispose()


async def _borrar_esquema() -> None:
    motor = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    async with motor.begin() as connection:
        await connection.execute(text(f'DROP SCHEMA IF EXISTS "{settings.DB_SCHEMA}" CASCADE'))
    await motor.dispose()


@pytest.fixture(scope="session", autouse=True)
def prepare_database() -> Iterator[None]:
    # Sincrono a proposito: asi el montaje no comparte event loop con los tests,
    # que cada uno corre en el suyo.
    asyncio.run(_crear_esquema())
    yield
    asyncio.run(_borrar_esquema())
    shutil.rmtree(Path(settings.LOCAL_STORAGE_PATH), ignore_errors=True)


@pytest.fixture(autouse=True)
async def clean_tables() -> AsyncIterator[None]:
    tablas = ", ".join(f'"{settings.DB_SCHEMA}".{tabla}' for tabla in TABLES)
    async with engine.begin() as connection:
        await connection.execute(text(f"TRUNCATE {tablas} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app = create_app()
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://tests"
    ) as http_client:
        yield http_client


@pytest.fixture
def login_as(client: AsyncClient, api: str) -> Callable[..., Awaitable[dict[str, str]]]:
    """Registra una cuenta, inicia sesion y devuelve la cabecera de autorizacion."""

    async def _login(
        email: str = "victor@memories.app",
        password: str = "unaClaveSegura1",
        display_name: str = "Victor",
    ) -> dict[str, str]:
        await client.post(
            f"{api}/auth/register",
            json={"email": email, "display_name": display_name, "password": password},
        )
        response = await client.post(
            f"{api}/auth/login", json={"email": email, "password": password}
        )
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _login


@pytest.fixture
async def auth_headers(
    login_as: Callable[..., Awaitable[dict[str, str]]],
) -> dict[str, str]:
    return await login_as()
