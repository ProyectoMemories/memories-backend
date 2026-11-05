"""Login, refresh y logout contra PostgreSQL, en Android y en web (HU-03 a HU-05)."""

import re
import uuid
from datetime import UTC, datetime, timedelta
from http.cookies import SimpleCookie
from typing import Any

import jwt
import psycopg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response
from pwdlib.hashers.argon2 import Argon2Hasher

from app.modules.auth.passwords import PasswordHasher
from app.modules.auth.router import REFRESH_COOKIE, CurrentUser
from app.modules.auth.tokens import create_access_token
from tests.conftest import SECRET_KEY, WEB_APP_ORIGIN, FakeEmailSender

REGISTER = "/api/v1/auth/register"
VERIFY = "/api/v1/auth/verify-email"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/test/me"
PASSWORD = "caballo bateria grapa"
WEB = {"Origin": WEB_APP_ORIGIN}


# ─── Ayudas ────────────────────────────────────────────────────────────────


@pytest.fixture
def api(db_client: TestClient) -> TestClient:
    """La API con una ruta protegida de prueba, para usar el "usuario actual"."""
    app: FastAPI = db_client.app  # type: ignore[assignment]

    @app.get(ME)
    def me(user: CurrentUser) -> dict[str, str]:
        return {"username": user.username}

    return db_client


def _create_user(
    api: TestClient,
    outbox: FakeEmailSender,
    username: str = "ana.rios",
    verify: bool = True,
) -> None:
    data = {
        "username": username,
        "email": f"{username}@correo.com",
        "password": PASSWORD,
        "first_name": "Ana",
        "paternal_surname": "Ríos",
        "birth_date": "2000-05-17",
        "accepts_privacy_policy": True,
    }
    assert api.post(REGISTER, json=data).status_code == 201
    if verify:
        token = re.search(r"token=(\S+)", outbox.sent[-1].text).group(1)
        assert api.post(VERIFY, json={"token": token}).status_code == 204


def _login(
    api: TestClient, platform: str, identifier: str = "ana.rios", **extra: Any
) -> Response:
    body = {"identifier": identifier, "password": PASSWORD, "platform": platform}
    return api.post(LOGIN, json={**body, **extra})


def _web_cookie(response: Response) -> SimpleCookie:
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    return cookie


def _with_cookie(token: str) -> dict[str, str]:
    # El cliente de pruebas usa http, así que no reenvía una cookie Secure:
    # se manda a mano, como lo haría el navegador.
    return {**WEB, "Cookie": f"{REFRESH_COOKIE}={token}"}


def _sql(migrated_db: str, query: str, params: tuple = ()) -> list[tuple]:
    with psycopg.connect(migrated_db, autocommit=True) as conn:
        cursor = conn.execute(query, params)
        return cursor.fetchall() if cursor.description else []


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ─── HU-03 Iniciar sesión ──────────────────────────────────────────────────


def test_login_android_entrega_los_dos_tokens_en_el_cuerpo(
    api: TestClient, outbox: FakeEmailSender, migrated_db: str
) -> None:
    _create_user(api, outbox)

    response = _login(api, "android", identifier="ANA.RIOS", device_name="Pixel 8")

    assert response.status_code == 200
    assert "set-cookie" not in response.headers
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 15 * 60
    session_id, secret = body["refresh_token"].split(".")

    claims = jwt.decode(body["access_token"], SECRET_KEY, algorithms=["HS256"])
    assert claims["type"] == "access"
    assert claims["sid"] == session_id

    [(platform, device, token_hash, lifetime)] = _sql(
        migrated_db,
        "SELECT platform, device_name, refresh_token_hash, expires_at - created_at "
        "FROM user_session WHERE id = %s",
        (uuid.UUID(session_id),),
    )
    assert (platform, device, lifetime) == ("android", "Pixel 8", timedelta(days=30))
    assert secret not in token_hash  # solo se guarda el hash
    assert api.get(ME, headers=_bearer(body["access_token"])).json() == {
        "username": "ana.rios"
    }


def test_login_web_entrega_el_token_de_renovacion_en_una_cookie(
    api: TestClient, outbox: FakeEmailSender, migrated_db: str
) -> None:
    _create_user(api, outbox)

    response = _login(api, "web", identifier="Ana.Rios@Correo.com")

    assert response.status_code == 200
    assert "refresh_token" not in response.json()
    cookie = _web_cookie(response)[REFRESH_COOKIE]
    assert cookie["httponly"] is True
    assert cookie["secure"] is True
    assert cookie["samesite"] == "strict"
    assert cookie["path"] == "/api/v1/auth"
    assert cookie["max-age"] == str(30 * 24 * 3600)
    session_id = uuid.UUID(cookie.value.split(".")[0])
    assert _sql(
        migrated_db, "SELECT platform FROM user_session WHERE id = %s", (session_id,)
    ) == [("web",)]


@pytest.mark.parametrize("identifier", ["ana.rios", "nadie.existe"])
def test_credenciales_incorrectas_dan_el_mismo_error(
    api: TestClient, outbox: FakeEmailSender, identifier: str
) -> None:
    _create_user(api, outbox)

    response = api.post(
        LOGIN,
        json={"identifier": identifier, "password": "otra cosa", "platform": "web"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "code": "invalid_credentials",
        "message": "El usuario o la contraseña no son correctos.",
    }


def test_sin_verificar_solo_se_entera_con_la_contrasena_correcta(
    api: TestClient, outbox: FakeEmailSender
) -> None:
    _create_user(api, outbox, verify=False)

    wrong = api.post(
        LOGIN,
        json={"identifier": "ana.rios", "password": "otra cosa", "platform": "web"},
    )
    right = _login(api, "web")

    assert (wrong.status_code, wrong.json()["code"]) == (401, "invalid_credentials")
    assert (right.status_code, right.json()["code"]) == (403, "email_not_verified")


def test_cuenta_suspendida_no_entra(
    api: TestClient, outbox: FakeEmailSender, migrated_db: str
) -> None:
    _create_user(api, outbox)
    _sql(
        migrated_db,
        "UPDATE app_user SET status = 'suspended', suspended_at = now()",
    )

    response = _login(api, "android")

    assert (response.status_code, response.json()["code"]) == (403, "account_suspended")


def test_cuenta_desactivada_se_reactiva_al_entrar(
    api: TestClient, outbox: FakeEmailSender, migrated_db: str
) -> None:
    _create_user(api, outbox)
    _sql(migrated_db, "UPDATE app_user SET status = 'deactivated'")

    assert _login(api, "android").status_code == 200
    assert _sql(migrated_db, "SELECT status FROM app_user") == [("active",)]


@pytest.mark.parametrize(
    ("days_ago", "can_log_in"), [(29, True), (30, False)], ids=["dentro", "vencida"]
)
def test_eliminacion_pendiente_se_cancela_dentro_de_los_30_dias(
    api: TestClient,
    outbox: FakeEmailSender,
    migrated_db: str,
    days_ago: int,
    can_log_in: bool,
) -> None:
    _create_user(api, outbox)
    _sql(
        migrated_db,
        "UPDATE app_user SET status = 'pending_deletion', "
        "deletion_requested_at = now() - make_interval(days => %s)",
        (days_ago,),
    )

    response = _login(api, "android")

    if can_log_in:
        assert response.status_code == 200
        assert _sql(
            migrated_db, "SELECT status, deletion_requested_at FROM app_user"
        ) == [("active", None)]
    else:
        assert response.json()["code"] == "invalid_credentials"


def test_sexto_login_en_un_minuto_se_rechaza(
    api: TestClient, outbox: FakeEmailSender
) -> None:
    _create_user(api, outbox)
    for _ in range(5):
        assert _login(api, "android").status_code == 200

    response = _login(api, "android")

    assert (response.status_code, response.json()["code"]) == (429, "too_many_requests")


def test_rehace_el_hash_si_usa_parametros_viejos(
    api: TestClient, outbox: FakeEmailSender, migrated_db: str
) -> None:
    _create_user(api, outbox)
    old_hash = PasswordHasher(Argon2Hasher(time_cost=1)).hash(PASSWORD)
    _sql(migrated_db, "UPDATE app_user SET password_hash = %s", (old_hash,))

    assert _login(api, "android").status_code == 200
    [(new_hash,)] = _sql(migrated_db, "SELECT password_hash FROM app_user")
    assert new_hash != old_hash


# ─── Token de acceso y usuario actual (RN-67) ──────────────────────────────


def test_sin_token_de_acceso_responde_401(api: TestClient) -> None:
    response = api.get(ME)

    assert response.status_code == 401
    assert response.json()["code"] == "not_authenticated"
    assert response.headers["www-authenticate"] == "Bearer"


def test_token_de_acceso_vencido_pide_renovar(
    api: TestClient, outbox: FakeEmailSender
) -> None:
    _create_user(api, outbox)
    access = _login(api, "android").json()["access_token"]
    claims = jwt.decode(access, SECRET_KEY, algorithms=["HS256"])
    expired = create_access_token(
        uuid.UUID(claims["sub"]),
        uuid.UUID(claims["sid"]),
        timedelta(minutes=15),
        SECRET_KEY,
        datetime.now(UTC) - timedelta(minutes=16),
    )

    response = api.get(ME, headers=_bearer(expired))

    assert (response.status_code, response.json()["code"]) == (
        401,
        "access_token_expired",
    )


def test_enlace_de_verificacion_no_sirve_como_token_de_acceso(
    api: TestClient, outbox: FakeEmailSender
) -> None:
    # Está firmado con la misma SECRET_KEY, pero no lleva type "access".
    _create_user(api, outbox, verify=False)
    verification_token = re.search(r"token=(\S+)", outbox.sent[-1].text).group(1)

    response = api.get(ME, headers=_bearer(verification_token))

    assert (response.status_code, response.json()["code"]) == (
        401,
        "not_authenticated",
    )


def test_token_firmado_sin_tipo_access_se_rechaza(
    api: TestClient, outbox: FakeEmailSender
) -> None:
    _create_user(api, outbox)
    access = _login(api, "android").json()["access_token"]
    claims = jwt.decode(access, SECRET_KEY, algorithms=["HS256"])
    del claims["type"]
    forged = jwt.encode(claims, SECRET_KEY, algorithm="HS256")

    assert api.get(ME, headers=_bearer(forged)).status_code == 401


def test_cuenta_suspendida_con_token_vigente_es_rechazada(
    api: TestClient, outbox: FakeEmailSender, migrated_db: str
) -> None:
    _create_user(api, outbox)
    access = _login(api, "android").json()["access_token"]
    assert api.get(ME, headers=_bearer(access)).status_code == 200

    _sql(migrated_db, "UPDATE app_user SET status = 'suspended', suspended_at = now()")

    assert api.get(ME, headers=_bearer(access)).status_code == 401


# ─── HU-04 Mantener la sesión ──────────────────────────────────────────────


def test_refresh_android_rota_el_token_y_alarga_la_sesion(
    api: TestClient, outbox: FakeEmailSender, migrated_db: str
) -> None:
    _create_user(api, outbox)
    first = _login(api, "android").json()
    session_id = uuid.UUID(first["refresh_token"].split(".")[0])
    _sql(
        migrated_db,
        "UPDATE user_session SET expires_at = now() + interval '1 day'",
    )

    response = api.post(REFRESH, json={"refresh_token": first["refresh_token"]})

    assert response.status_code == 200
    second = response.json()
    assert second["refresh_token"] != first["refresh_token"]
    assert second["refresh_token"].startswith(f"{session_id}.")
    assert api.get(ME, headers=_bearer(second["access_token"])).status_code == 200
    [(remaining,)] = _sql(migrated_db, "SELECT expires_at - now() FROM user_session")
    assert remaining > timedelta(days=29)


def test_reusar_un_token_ya_rotado_revoca_la_sesion(
    api: TestClient, outbox: FakeEmailSender, migrated_db: str
) -> None:
    _create_user(api, outbox)
    old = _login(api, "android").json()["refresh_token"]
    new = api.post(REFRESH, json={"refresh_token": old}).json()["refresh_token"]

    reused = api.post(REFRESH, json={"refresh_token": old})

    assert (reused.status_code, reused.json()["code"]) == (
        401,
        "invalid_refresh_token",
    )
    assert _sql(migrated_db, "SELECT revoked_at IS NOT NULL FROM user_session") == [
        (True,)
    ]
    # El token legítimo también deja de servir: hay que volver a entrar.
    assert api.post(REFRESH, json={"refresh_token": new}).status_code == 401


@pytest.mark.parametrize(
    "update",
    [
        "UPDATE user_session SET created_at = now() - interval '31 days', "
        "expires_at = now() - interval '1 second'",
        "UPDATE user_session SET revoked_at = now()",
    ],
    ids=["vencida", "revocada"],
)
def test_refresh_de_sesion_vencida_o_revocada_se_rechaza(
    api: TestClient, outbox: FakeEmailSender, migrated_db: str, update: str
) -> None:
    _create_user(api, outbox)
    token = _login(api, "android").json()["refresh_token"]
    _sql(migrated_db, update)
    [before] = _sql(migrated_db, "SELECT * FROM user_session")

    response = api.post(REFRESH, json={"refresh_token": token})

    assert response.status_code == 401
    assert _sql(migrated_db, "SELECT * FROM user_session") == [before]


@pytest.mark.parametrize(
    "token", ["basura", "0193b0a0-0000-7000-8000-000000000000.secreto"]
)
def test_refresh_con_token_inventado_se_rechaza(api: TestClient, token: str) -> None:
    response = api.post(REFRESH, json={"refresh_token": token})

    assert (response.status_code, response.json()["code"]) == (
        401,
        "invalid_refresh_token",
    )


def test_refresh_de_cuenta_suspendida_se_rechaza(
    api: TestClient, outbox: FakeEmailSender, migrated_db: str
) -> None:
    _create_user(api, outbox)
    token = _login(api, "android").json()["refresh_token"]
    _sql(migrated_db, "UPDATE app_user SET status = 'suspended', suspended_at = now()")

    assert api.post(REFRESH, json={"refresh_token": token}).status_code == 401


def test_refresh_web_con_cookie_y_origen_de_la_app(
    api: TestClient, outbox: FakeEmailSender
) -> None:
    _create_user(api, outbox)
    old = _web_cookie(_login(api, "web"))[REFRESH_COOKIE].value

    response = api.post(REFRESH, headers=_with_cookie(old))

    assert response.status_code == 200
    assert "refresh_token" not in response.json()
    new = _web_cookie(response)[REFRESH_COOKIE].value
    assert new != old
    assert (
        api.get(ME, headers=_bearer(response.json()["access_token"])).status_code == 200
    )


@pytest.mark.parametrize(
    "origin", [None, "https://evil.example", "http://localhost:8001"]
)
def test_refresh_web_desde_otro_origen_se_rechaza(
    api: TestClient, outbox: FakeEmailSender, origin: str | None
) -> None:
    _create_user(api, outbox)
    token = _web_cookie(_login(api, "web"))[REFRESH_COOKIE].value
    headers = {"Cookie": f"{REFRESH_COOKIE}={token}"}
    if origin is not None:
        headers["Origin"] = origin

    response = api.post(REFRESH, headers=headers)

    assert (response.status_code, response.json()["code"]) == (
        403,
        "origin_not_allowed",
    )
    # La sesión sigue sirviendo desde la app web.
    assert api.post(REFRESH, headers=_with_cookie(token)).status_code == 200


def test_cada_token_solo_sirve_por_el_canal_de_su_plataforma(
    api: TestClient, outbox: FakeEmailSender
) -> None:
    _create_user(api, outbox)
    android = _login(api, "android").json()["refresh_token"]
    web = _web_cookie(_login(api, "web"))[REFRESH_COOKIE].value

    assert api.post(REFRESH, headers=_with_cookie(android)).status_code == 401
    assert api.post(REFRESH, json={"refresh_token": web}).status_code == 401


def test_refresh_web_sin_cookie_se_rechaza(api: TestClient) -> None:
    response = api.post(REFRESH, headers=WEB)

    assert (response.status_code, response.json()["code"]) == (
        401,
        "invalid_refresh_token",
    )


# ─── HU-05 Cerrar sesión ───────────────────────────────────────────────────


def test_logout_android_revoca_solo_esa_sesion(
    api: TestClient, outbox: FakeEmailSender
) -> None:
    _create_user(api, outbox)
    phone = _login(api, "android").json()["refresh_token"]
    tablet = _login(api, "android").json()["refresh_token"]

    first = api.post(LOGOUT, json={"refresh_token": phone})
    second = api.post(LOGOUT, json={"refresh_token": phone})

    assert (first.status_code, second.status_code) == (204, 204)
    assert api.post(REFRESH, json={"refresh_token": phone}).status_code == 401
    assert api.post(REFRESH, json={"refresh_token": tablet}).status_code == 200


def test_logout_web_revoca_la_sesion_y_borra_la_cookie(
    api: TestClient, outbox: FakeEmailSender
) -> None:
    _create_user(api, outbox)
    token = _web_cookie(_login(api, "web"))[REFRESH_COOKIE].value

    response = api.post(LOGOUT, headers=_with_cookie(token))

    assert response.status_code == 204
    cookie = _web_cookie(response)[REFRESH_COOKIE]
    assert cookie.value == ""
    assert cookie["max-age"] == "0"
    assert cookie["path"] == "/api/v1/auth"
    assert api.post(REFRESH, headers=_with_cookie(token)).status_code == 401
    # Otra vez, ya sin sesión, tampoco da error.
    assert api.post(LOGOUT, headers=_with_cookie(token)).status_code == 204


def test_logout_web_desde_otro_origen_se_rechaza(
    api: TestClient, outbox: FakeEmailSender
) -> None:
    _create_user(api, outbox)
    token = _web_cookie(_login(api, "web"))[REFRESH_COOKIE].value

    response = api.post(
        LOGOUT,
        headers={
            "Origin": "https://evil.example",
            "Cookie": f"{REFRESH_COOKIE}={token}",
        },
    )

    assert response.status_code == 403
    assert api.post(REFRESH, headers=_with_cookie(token)).status_code == 200


def test_logout_sin_token_no_da_error(api: TestClient) -> None:
    assert api.post(LOGOUT, headers=WEB).status_code == 204


# ─── El token de acceso muere con su sesión (D56) ──────────────────────────


def test_tras_el_logout_android_el_token_de_acceso_deja_de_servir(
    api: TestClient, outbox: FakeEmailSender
) -> None:
    _create_user(api, outbox)
    tokens = _login(api, "android").json()
    assert api.get(ME, headers=_bearer(tokens["access_token"])).status_code == 200

    api.post(LOGOUT, json={"refresh_token": tokens["refresh_token"]})

    response = api.get(ME, headers=_bearer(tokens["access_token"]))
    # not_authenticated, no access_token_expired: renovar tampoco serviría.
    assert (response.status_code, response.json()["code"]) == (
        401,
        "not_authenticated",
    )


def test_tras_el_logout_web_el_token_de_acceso_deja_de_servir(
    api: TestClient, outbox: FakeEmailSender
) -> None:
    _create_user(api, outbox)
    response = _login(api, "web")
    access = response.json()["access_token"]
    refresh = _web_cookie(response)[REFRESH_COOKIE].value

    api.post(LOGOUT, headers=_with_cookie(refresh))

    assert api.get(ME, headers=_bearer(access)).status_code == 401


def test_cerrar_una_sesion_no_corta_el_acceso_de_otra(
    api: TestClient, outbox: FakeEmailSender
) -> None:
    _create_user(api, outbox)
    phone = _login(api, "android").json()
    laptop = _login(api, "web").json()

    api.post(LOGOUT, json={"refresh_token": phone["refresh_token"]})

    assert api.get(ME, headers=_bearer(laptop["access_token"])).status_code == 200


def test_reuso_del_token_de_renovacion_corta_tambien_el_acceso(
    api: TestClient, outbox: FakeEmailSender
) -> None:
    _create_user(api, outbox)
    old = _login(api, "android").json()
    new = api.post(REFRESH, json={"refresh_token": old["refresh_token"]}).json()

    api.post(REFRESH, json={"refresh_token": old["refresh_token"]})  # reuso

    assert api.get(ME, headers=_bearer(new["access_token"])).status_code == 401


def test_sesion_vencida_corta_el_acceso(
    api: TestClient, outbox: FakeEmailSender, migrated_db: str
) -> None:
    _create_user(api, outbox)
    access = _login(api, "android").json()["access_token"]
    _sql(
        migrated_db,
        "UPDATE user_session SET created_at = now() - interval '31 days', "
        "expires_at = now() - interval '1 second'",
    )

    assert api.get(ME, headers=_bearer(access)).status_code == 401


def test_token_con_sesion_de_otra_cuenta_se_rechaza(
    api: TestClient, outbox: FakeEmailSender
) -> None:
    _create_user(api, outbox, username="ana.rios")
    _create_user(api, outbox, username="luis.paz")
    ana = jwt.decode(
        _login(api, "android", identifier="ana.rios").json()["access_token"],
        SECRET_KEY,
        algorithms=["HS256"],
    )
    luis = jwt.decode(
        _login(api, "android", identifier="luis.paz").json()["access_token"],
        SECRET_KEY,
        algorithms=["HS256"],
    )
    # Firmado bien, pero mezcla el usuario de Ana con la sesión de Luis.
    mixed = create_access_token(
        uuid.UUID(ana["sub"]),
        uuid.UUID(luis["sid"]),
        timedelta(minutes=15),
        SECRET_KEY,
        datetime.now(UTC),
    )

    assert api.get(ME, headers=_bearer(mixed)).status_code == 401
