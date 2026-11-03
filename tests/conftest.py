import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

WEB_APP_ORIGIN = "http://localhost:3000"
# La API no se conecta a la base en estas pruebas; basta con una URL válida.
DATABASE_URL = "postgresql+psycopg://memories:memories@localhost:5432/memories"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        app_env="test", web_app_origin=WEB_APP_ORIGIN, database_url=DATABASE_URL
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))
