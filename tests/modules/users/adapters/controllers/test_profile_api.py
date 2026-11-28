"""GET /api/v1/users/me contra PostgreSQL (HU-01, RNF-02)."""

import re

import pytest
from fastapi.testclient import TestClient

from tests.conftest import FakeEmailSender

ME = "/api/v1/users/me"
PASSWORD = "caballo bateria grapa"


def _register_and_log_in(
    api: TestClient,
    outbox: FakeEmailSender,
    username: str,
    first_name: str,
    maternal_surname: str | None = None,
) -> dict[str, str]:
    """Crea y verifica la cuenta, inicia sesión en Android y devuelve los tokens."""
    data = {
        "username": username,
        "email": f"{username}@correo.com",
        "password": PASSWORD,
        "first_name": first_name,
        "paternal_surname": "Ríos",
        "maternal_surname": maternal_surname,
        "birth_date": "2000-05-17",
        "accepts_privacy_policy": True,
    }
    assert api.post("/api/v1/auth/register", json=data).status_code == 201
    match = re.search(r"token=(\S+)", outbox.sent[-1].text)
    assert match, "el correo no trae el enlace"
    verify = api.post("/api/v1/auth/verify-email", json={"token": match.group(1)})
    assert verify.status_code == 204
    login = api.post(
        "/api/v1/auth/login",
        json={"identifier": username, "password": PASSWORD, "platform": "android"},
    )
    assert login.status_code == 200
    tokens: dict[str, str] = login.json()
    return tokens


def _bearer(tokens: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_devuelve_mis_datos_y_nada_mas(
    db_client: TestClient, outbox: FakeEmailSender
) -> None:
    tokens = _register_and_log_in(
        db_client, outbox, "ana.rios", "Ana", maternal_surname="Paz"
    )

    response = db_client.get(ME, headers=_bearer(tokens))

    assert response.status_code == 200
    body = response.json()
    # Sin fecha de nacimiento, hash, estado ni superusuario (privacidad).
    assert set(body) == {
        "id",
        "username",
        "email",
        "first_name",
        "paternal_surname",
        "maternal_surname",
    }
    assert body["username"] == "ana.rios"
    assert body["email"] == "ana.rios@correo.com"
    assert (body["first_name"], body["paternal_surname"], body["maternal_surname"]) == (
        "Ana",
        "Ríos",
        "Paz",
    )


def test_apellido_materno_vacio_llega_como_null(
    db_client: TestClient, outbox: FakeEmailSender
) -> None:
    tokens = _register_and_log_in(db_client, outbox, "ana.rios", "Ana")

    body = db_client.get(ME, headers=_bearer(tokens)).json()

    assert body["maternal_surname"] is None


def test_dos_cuentas_cada_una_ve_solo_lo_suyo(
    db_client: TestClient, outbox: FakeEmailSender
) -> None:
    """RNF-02: no hay forma de pedir el perfil de otra cuenta."""
    ana = _register_and_log_in(db_client, outbox, "ana.rios", "Ana")
    luis = _register_and_log_in(db_client, outbox, "luis.paz", "Luis")

    ana_body = db_client.get(ME, headers=_bearer(ana)).json()
    luis_body = db_client.get(ME, headers=_bearer(luis)).json()

    assert (ana_body["username"], ana_body["first_name"]) == ("ana.rios", "Ana")
    assert (luis_body["username"], luis_body["first_name"]) == ("luis.paz", "Luis")
    assert ana_body["id"] != luis_body["id"]


def test_sin_token_responde_401(db_client: TestClient) -> None:
    response = db_client.get(ME)

    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


@pytest.mark.parametrize("token", ["no-es-un-jwt", "a.b.c"])
def test_token_invalido_responde_401(db_client: TestClient, token: str) -> None:
    response = db_client.get(ME, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"


def test_sesion_cerrada_responde_401(
    db_client: TestClient, outbox: FakeEmailSender
) -> None:
    """Cerrar sesión corta también el token de acceso (RN-67)."""
    tokens = _register_and_log_in(db_client, outbox, "ana.rios", "Ana")
    logout = db_client.post(
        "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert logout.status_code == 204

    response = db_client.get(ME, headers=_bearer(tokens))

    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"
