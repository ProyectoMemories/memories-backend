import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from tests.conftest import (
    DATABASE_URL,
    PRIVACY_POLICY_VERSION,
    SECRET_KEY,
    WEB_APP_ORIGIN,
)

_REQUIRED = {
    "database_url": DATABASE_URL,
    "secret_key": SECRET_KEY,
    "privacy_policy_version": PRIVACY_POLICY_VERSION,
}


@pytest.mark.parametrize(
    "origin",
    ["*", "localhost:3000", "http://localhost:3000/", "http://a.com,http://b.com"],
)
def test_rechaza_origenes_invalidos(origin: str) -> None:
    with pytest.raises(ValidationError):
        Settings(web_app_origin=origin, **_REQUIRED)


def test_rechaza_entorno_desconocido() -> None:
    with pytest.raises(ValidationError):
        Settings(app_env="staging", web_app_origin=WEB_APP_ORIGIN, **_REQUIRED)


def test_rechaza_url_de_base_sin_psycopg() -> None:
    with pytest.raises(ValidationError):
        Settings(
            **{
                **_REQUIRED,
                "database_url": "postgresql://memories:memories@localhost:5432/x",
            },
            web_app_origin=WEB_APP_ORIGIN,
        )


def test_rechaza_clave_secreta_corta() -> None:
    with pytest.raises(ValidationError):
        Settings(**{**_REQUIRED, "secret_key": "corta"}, web_app_origin=WEB_APP_ORIGIN)


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
