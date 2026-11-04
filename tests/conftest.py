"""Fixtures comunes: configuración, cliente HTTP y base de pruebas en PostgreSQL."""

import os
from collections.abc import Iterator
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from psycopg import sql
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

from app.config import Settings
from app.email import EmailMessage
from app.main import create_app

ROOT = Path(__file__).resolve().parents[1]

WEB_APP_ORIGIN = "http://localhost:3000"
# La API no se conecta a la base en las pruebas que usan `client`.
DATABASE_URL = "postgresql+psycopg://memories:memories@localhost:5432/memories"
SECRET_KEY = "clave-solo-para-pruebas-con-mas-de-32-caracteres"
PRIVACY_POLICY_VERSION = "2026-11"


def make_settings(database_url: str = DATABASE_URL) -> Settings:
    return Settings(
        app_env="test",
        web_app_origin=WEB_APP_ORIGIN,
        database_url=database_url,
        secret_key=SECRET_KEY,
        privacy_policy_version=PRIVACY_POLICY_VERSION,
    )


class FakeEmailSender:
    """Guarda los correos en una lista en lugar de enviarlos."""

    def __init__(self) -> None:
        self.sent: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self.sent.append(message)


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings, email_sender=FakeEmailSender()))


# ─── Base de pruebas (PostgreSQL real) ─────────────────────────────────────
# Su nombre debe terminar en `_test`: se borra y se crea de nuevo en cada
# corrida, así que nunca toca tus datos de desarrollo.


class _TestDatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    test_database_url: str | None = None


def _alembic_config(url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    config.attributes["configure_logger"] = False
    return config


def _libpq_url(url: str) -> str:
    """psycopg no entiende el prefijo `postgresql+psycopg://` de SQLAlchemy."""
    return (
        make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)
    )


@pytest.fixture(scope="session")
def database_url() -> str:
    url = _TestDatabaseSettings().test_database_url
    if not url:
        if os.environ.get("CI"):
            pytest.fail("En el CI falta TEST_DATABASE_URL")
        pytest.skip(
            "Falta TEST_DATABASE_URL en tu .env. Levanta la base con "
            "`docker compose up -d db` (ver README)."
        )

    name = make_url(url).database or ""
    if not name.endswith("_test"):
        pytest.fail(f"La base de pruebas debe terminar en '_test' (es '{name}')")

    # Se recrea la base desde cero conectándose a la base 'postgres'.
    admin_url = _libpq_url(
        make_url(url).set(database="postgres").render_as_string(hide_password=False)
    )
    try:
        with psycopg.connect(admin_url, autocommit=True) as admin:
            admin.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                    sql.Identifier(name)
                )
            )
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    except psycopg.OperationalError as error:
        if os.environ.get("CI"):
            raise
        pytest.skip(f"No se pudo conectar a PostgreSQL: {error}")
    return url


@pytest.fixture(scope="session")
def alembic_config(database_url: str) -> Config:
    return _alembic_config(database_url)


@pytest.fixture(scope="session")
def migrated_db(database_url: str, alembic_config: Config) -> str:
    command.upgrade(alembic_config, "head")
    return _libpq_url(database_url)


# ─── API contra la base de pruebas ─────────────────────────────────────────


@pytest.fixture
def outbox() -> FakeEmailSender:
    return FakeEmailSender()


@pytest.fixture
def db_client(
    migrated_db: str, database_url: str, outbox: FakeEmailSender
) -> Iterator[TestClient]:
    """Cliente con la API conectada a la base de pruebas.

    La API confirma sus transacciones, así que al terminar se vacían las tablas.
    """
    app = create_app(make_settings(database_url), email_sender=outbox)
    with TestClient(app) as test_client:
        yield test_client
    app.state.sessionmaker.kw["bind"].dispose()
    with psycopg.connect(migrated_db, autocommit=True) as connection:
        connection.execute("TRUNCATE app_user CASCADE")
