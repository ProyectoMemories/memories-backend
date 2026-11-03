from fastapi.testclient import TestClient


def test_health_responde_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_aparece_en_openapi(client: TestClient) -> None:
    # El frontend genera su cliente desde este documento (D57).
    paths = client.get("/openapi.json").json()["paths"]

    assert "/health" in paths
