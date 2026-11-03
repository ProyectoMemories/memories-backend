import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from tests.conftest import WEB_APP_ORIGIN


@pytest.mark.parametrize(
    "origin",
    ["*", "localhost:3000", "http://localhost:3000/", "http://a.com,http://b.com"],
)
def test_rechaza_origenes_invalidos(origin: str) -> None:
    with pytest.raises(ValidationError):
        Settings(web_app_origin=origin)


def test_rechaza_entorno_desconocido() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="staging", web_app_origin=WEB_APP_ORIGIN)


def test_cors_acepta_el_origen_de_la_app_web(client: TestClient) -> None:
    response = client.options(
        "/health",
        headers={"Origin": WEB_APP_ORIGIN, "Access-Control-Request-Method": "GET"},
    )

    assert response.headers["access-control-allow-origin"] == WEB_APP_ORIGIN
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_no_acepta_otros_origenes(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers
