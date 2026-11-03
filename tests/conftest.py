import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

WEB_APP_ORIGIN = "http://localhost:3000"


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="test", web_app_origin=WEB_APP_ORIGIN)


@pytest.fixture
def client(settings: Settings) -> TestClient:
    return TestClient(create_app(settings))
