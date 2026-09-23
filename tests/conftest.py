"""Configuracion comun de los tests.

Las variables de entorno se fijan ANTES de importar la app: la configuracion se
lee una sola vez al importarse.

Los tests unitarios (tests/unit/) no necesitan ninguna infraestructura. Lo que
hace falta base de datos vive en tests/integration/conftest.py.
"""

import os

os.environ.setdefault("ENV", "testing")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("DB_SCHEMA", "memories_test")
os.environ.setdefault("CACHE_PROVIDER", "memory")
os.environ.setdefault("STORAGE_PROVIDER", "local")
os.environ.setdefault("LOCAL_STORAGE_PATH", "./.pytest_storage")
os.environ.setdefault("JWT_SECRET_KEY", "clave-solo-para-tests-no-usar-fuera")
os.environ.setdefault("PASSWORD_HASHING_SCHEME", "bcrypt")
# Menos rondas: en tests interesa la correccion, no el coste.
os.environ.setdefault("BCRYPT_ROUNDS", "4")
os.environ.setdefault("RATE_LIMIT_AUTH_PER_MINUTE", "1000")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://memories:memories@localhost:5433/memories",
)

# Estas variables mandan aunque el entorno traiga otras: los tests no deben
# depender de Redis ni de MinIO, ni escribir en el esquema de desarrollo.
os.environ["ENV"] = "testing"
os.environ["DB_SCHEMA"] = "memories_test"
os.environ["CACHE_PROVIDER"] = "memory"
os.environ["STORAGE_PROVIDER"] = "local"
os.environ["RATE_LIMIT_AUTH_PER_MINUTE"] = "1000"
os.environ["BCRYPT_ROUNDS"] = "4"

import pytest  # noqa: E402

from app.config.settings import get_settings  # noqa: E402

settings = get_settings()


@pytest.fixture
def api() -> str:
    """Prefijo de la API, para no repetirlo en cada llamada."""
    return settings.API_PREFIX


@pytest.fixture
def png() -> bytes:
    """Imagen PNG minima que pasa la comprobacion de firma."""
    return b"\x89PNG\r\n\x1a\n" + b"0" * 64
