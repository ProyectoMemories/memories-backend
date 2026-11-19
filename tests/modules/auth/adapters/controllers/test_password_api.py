"""Recuperar y cambiar la contraseña por HTTP, en Android y web (HU-06, HU-07)."""

import re
from http.cookies import SimpleCookie
from typing import Any
from urllib.parse import parse_qs, urlparse

import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response

from app.modules.auth.adapters.controllers.dependencies import CurrentUser
from app.modules.auth.adapters.presenters.refresh_cookie import REFRESH_COOKIE
from tests.conftest import WEB_APP_ORIGIN, FakeEmailSender

AUTH = "/api/v1/auth"
ME = "/test/me"
PASSWORD = "caballo bateria grapa"
NEW_PASSWORD = "otra frase larga y nueva"


@pytest.fixture
def api(db_client: TestClient, outbox: FakeEmailSender) -> TestClient:
    """API con una ruta protegida de prueba y una cuenta verificada (ana.rios)."""
    app: FastAPI = db_client.app  # type: ignore[assignment]

    @app.get(ME)
    def me(user: CurrentUser) -> dict[str, str]:
        return {"username": user.username}

    data = {
        "username": "ana.rios",
        "email": "ana@correo.com",
        "password": PASSWORD,
        "first_name": "Ana",
        "paternal_surname": "Ríos",
        "birth_date": "2000-05-17",
        "accepts_privacy_policy": True,
    }
    assert db_client.post(f"{AUTH}/register", json=data).status_code == 201
    verify_token = _link_token(outbox, "/verify-email")
    response = db_client.post(f"{AUTH}/verify-email", json={"token": verify_token})
    assert response.status_code == 204
    outbox.sent.clear()
    return db_client


def _link_token(outbox: FakeEmailSender, path: str) -> str:
    match = re.search(rf"\S+{path}\?\S+", outbox.sent[-1].text)
    assert match, f"el correo no trae el enlace {path}"
    [token] = parse_qs(urlparse(match.group(0)).query)["token"]
    return token


def _login(api: TestClient, platform: str, password: str = PASSWORD) -> Response:
    body = {"identifier": "ana.rios", "password": password, "platform": platform}
    return api.post(f"{AUTH}/login", json=body)


def _android_and_web(api: TestClient) -> tuple[dict[str, Any], str, str]:
    """Tokens de una sesión Android y de una web."""
    android = _login(api, "android").json()
    web = _login(api, "web")
    cookie = SimpleCookie()
    cookie.load(web.headers["set-cookie"])
    return android, web.json()["access_token"], cookie[REFRESH_COOKIE].value


def _assert_all_sessions_closed(
    api: TestClient, android: dict[str, Any], web_access: str, web_refresh: str
) -> None:
    for access in (android["access_token"], web_access):
        assert (
            api.get(ME, headers={"Authorization": f"Bearer {access}"}).status_code
            == 401
        )
    android_refresh = {"refresh_token": android["refresh_token"]}
    assert api.post(f"{AUTH}/refresh", json=android_refresh).status_code == 401
    web_headers = {
        "Origin": WEB_APP_ORIGIN,
        "Cookie": f"{REFRESH_COOKIE}={web_refresh}",
    }
    assert api.post(f"{AUTH}/refresh", headers=web_headers).status_code == 401


def _forgot(api: TestClient, email: str = "ana@correo.com") -> Response:
    return api.post(f"{AUTH}/password/forgot", json={"email": email})


def _reset(api: TestClient, token: str, password: str = NEW_PASSWORD) -> Response:
    body = {"token": token, "new_password": password}
    return api.post(f"{AUTH}/password/reset", json=body)


# ─── HU-06 Recuperar la contraseña ─────────────────────────────────────────


def test_forgot_responde_igual_exista_o_no_la_cuenta(
    api: TestClient, outbox: FakeEmailSender
) -> None:
    existing, missing = _forgot(api, "ANA@correo.com"), _forgot(api, "nadie@correo.com")

    assert (existing.status_code, existing.content) == (202, b"")
    assert (missing.status_code, missing.content) == (202, b"")
    [email] = outbox.sent
    assert email.to == "ana@correo.com"
    assert f"{WEB_APP_ORIGIN}/reset-password?token=" in email.text


def test_cuenta_suspendida_no_recibe_el_enlace(
    api: TestClient, outbox: FakeEmailSender, migrated_db: str
) -> None:
    with psycopg.connect(migrated_db, autocommit=True) as conn:
        conn.execute("UPDATE app_user SET status = 'suspended', suspended_at = now()")

    assert _forgot(api).status_code == 202
    assert outbox.sent == []


def test_reset_guarda_la_nueva_y_cierra_todas_las_sesiones(
    api: TestClient, outbox: FakeEmailSender
) -> None:
    android, web_access, web_refresh = _android_and_web(api)
    _forgot(api)

    response = _reset(api, _link_token(outbox, "/reset-password"))

    assert response.status_code == 204
    _assert_all_sessions_closed(api, android, web_access, web_refresh)
    assert _login(api, "android").json()["code"] == "invalid_credentials"
    assert _login(api, "android", NEW_PASSWORD).status_code == 200


def test_el_enlace_sirve_una_sola_vez(api: TestClient, outbox: FakeEmailSender) -> None:
    _forgot(api)
    token = _link_token(outbox, "/reset-password")
    assert _reset(api, token).status_code == 204

    reused = _reset(api, token, "una tercera frase larga")

    assert (reused.status_code, reused.json()["code"]) == (400, "invalid_token")


@pytest.mark.parametrize("token", ["basura", "a.b.c"])
def test_enlace_alterado(api: TestClient, token: str) -> None:
    response = _reset(api, token)

    assert (response.status_code, response.json()["code"]) == (400, "invalid_token")


def test_contrasena_nueva_comun_se_rechaza_y_el_enlace_sigue_sirviendo(
    api: TestClient, outbox: FakeEmailSender
) -> None:
    _forgot(api)
    token = _link_token(outbox, "/reset-password")

    rejected = _reset(api, token, "Password1")

    assert (rejected.status_code, rejected.json()["code"]) == (
        422,
        "password_too_common",
    )
    assert _reset(api, token).status_code == 204


def test_sexto_pedido_de_recuperacion_en_un_minuto(api: TestClient) -> None:
    for _ in range(5):
        assert _forgot(api).status_code == 202

    assert _forgot(api).status_code == 429


# ─── HU-07 Cambiar la contraseña ───────────────────────────────────────────


def _change(api: TestClient, access: str | None, current: str = PASSWORD) -> Response:
    headers = {"Authorization": f"Bearer {access}"} if access else {}
    body = {"current_password": current, "new_password": NEW_PASSWORD}
    return api.post(f"{AUTH}/password/change", json=body, headers=headers)


def test_change_guarda_la_nueva_y_cierra_todas_las_sesiones(api: TestClient) -> None:
    android, web_access, web_refresh = _android_and_web(api)

    response = _change(api, android["access_token"])

    assert response.status_code == 204
    # También la sesión desde la que se cambió: la app vuelve al login (RN-67).
    _assert_all_sessions_closed(api, android, web_access, web_refresh)
    assert _login(api, "web", NEW_PASSWORD).status_code == 200


def test_contrasena_actual_incorrecta_no_cierra_nada(api: TestClient) -> None:
    android, web_access, _ = _android_and_web(api)

    response = _change(api, android["access_token"], current="otra cosa")

    assert (response.status_code, response.json()["code"]) == (
        422,
        "current_password_incorrect",
    )
    for access in (android["access_token"], web_access):
        assert (
            api.get(ME, headers={"Authorization": f"Bearer {access}"}).status_code
            == 200
        )


def test_change_sin_sesion(api: TestClient) -> None:
    response = _change(api, None)

    assert (response.status_code, response.json()["code"]) == (401, "not_authenticated")


def test_sexto_cambio_en_un_minuto(api: TestClient) -> None:
    access = _login(api, "android").json()["access_token"]
    for _ in range(5):
        assert _change(api, access, current="otra cosa").status_code == 422

    assert _change(api, access, current="otra cosa").status_code == 429
