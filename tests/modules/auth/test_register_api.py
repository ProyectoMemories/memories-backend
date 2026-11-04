"""Registro y verificación del correo contra PostgreSQL (HU-01, HU-02)."""

import re
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient

from app.modules.auth.tokens import TokenPurpose, create_email_token
from tests.conftest import (
    PRIVACY_POLICY_VERSION,
    SECRET_KEY,
    WEB_APP_ORIGIN,
    FakeEmailSender,
)

REGISTER = "/api/v1/auth/register"
VERIFY = "/api/v1/auth/verify-email"
RESEND = "/api/v1/auth/verify-email/resend"


def _years_ago(years: int, days: int = 0) -> date:
    today = datetime.now(UTC).date()
    if (today.month, today.day) == (2, 29):
        today -= timedelta(days=1)
    return today.replace(year=today.year - years) + timedelta(days=days)


def _registration(**changes: Any) -> dict[str, Any]:
    data = {
        "username": "ana.rios",
        "email": "Ana.Rios@Correo.com",
        "password": "caballo bateria grapa",
        "first_name": "Ana",
        "paternal_surname": "Ríos",
        "maternal_surname": None,
        "birth_date": "2000-05-17",
        "accepts_privacy_policy": True,
    }
    return {**data, **changes}


def _token_from(outbox: FakeEmailSender) -> str:
    match = re.search(r"/verify-email\?token=(\S+)", outbox.sent[-1].text)
    assert match, "el correo no trae el enlace"
    return match.group(1)


def _user_row(migrated_db: str, username: str) -> tuple:
    with psycopg.connect(migrated_db) as conn:
        row = conn.execute(
            "SELECT status, email_verified_at, is_superuser, password_hash "
            "FROM app_user WHERE username = %s",
            (username,),
        ).fetchone()
    assert row is not None
    return row


# ─── HU-01 Registrarse ─────────────────────────────────────────────────────


def test_registro_crea_cuenta_sin_verificar_y_envia_correo(
    db_client: TestClient, outbox: FakeEmailSender, migrated_db: str
) -> None:
    response = db_client.post(REGISTER, json=_registration())

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "ana.rios"
    assert body["status"] == "unverified"
    assert uuid.UUID(body["id"]).version == 7
    assert "password" not in str(body)

    status, verified_at, is_superuser, password_hash = _user_row(
        migrated_db, "ana.rios"
    )
    assert (status, verified_at, is_superuser) == ("unverified", None, False)
    assert password_hash.startswith("$argon2id$")

    with psycopg.connect(migrated_db) as conn:
        versions = conn.execute(
            "SELECT policy_version FROM privacy_consent WHERE user_id = %s",
            (uuid.UUID(body["id"]),),
        ).fetchall()
    assert versions == [(PRIVACY_POLICY_VERSION,)]

    [email] = outbox.sent
    assert email.to == body["email"]
    assert f"{WEB_APP_ORIGIN}/verify-email?token=" in email.text


def test_cumple_14_hoy_puede_registrarse(db_client: TestClient) -> None:
    response = db_client.post(
        REGISTER, json=_registration(birth_date=str(_years_ago(14)))
    )
    assert response.status_code == 201


def test_menor_de_14_no_se_registra_ni_se_guarda_nada(
    db_client: TestClient, outbox: FakeEmailSender, migrated_db: str
) -> None:
    birth_date = _years_ago(14, days=1)  # cumple 14 mañana

    response = db_client.post(REGISTER, json=_registration(birth_date=str(birth_date)))

    assert response.status_code == 422
    assert response.json()["code"] == "underage"
    assert outbox.sent == []
    with psycopg.connect(migrated_db) as conn:
        assert conn.execute("SELECT count(*) FROM app_user").fetchone() == (0,)


def test_sin_aceptar_la_politica_se_rechaza(db_client: TestClient) -> None:
    response = db_client.post(
        REGISTER, json=_registration(accepts_privacy_policy=False)
    )

    assert response.status_code == 422
    assert response.json()["code"] == "privacy_policy_not_accepted"


@pytest.mark.parametrize(
    ("field", "value"),
    [("username", "ANA.RIOS"), ("email", "ana.rios@correo.com")],
)
def test_usuario_o_correo_repetido_sin_importar_mayusculas(
    db_client: TestClient, field: str, value: str
) -> None:
    assert db_client.post(REGISTER, json=_registration()).status_code == 201

    other = _registration(username="otra.persona", email="otra@correo.com")
    response = db_client.post(REGISTER, json={**other, field: value})

    assert response.status_code == 409
    assert response.json()["code"] == f"{field}_taken"


@pytest.mark.parametrize(
    ("username", "message"),
    [
        ("an", "entre 3 y 30"),
        ("a" * 31, "entre 3 y 30"),
        ("ana-rios", "letras sin tilde"),
        ("josé", "letras sin tilde"),
        (".ana", "empezar ni terminar"),
        ("ana.", "empezar ni terminar"),
        ("ana..rios", "dos '.' seguidos"),
    ],
)
def test_formato_de_usuario_invalido_dice_que_esta_mal(
    db_client: TestClient, username: str, message: str
) -> None:
    response = db_client.post(REGISTER, json=_registration(username=username))

    assert response.status_code == 422
    [error] = response.json()["errors"]
    assert error["field"] == "username"
    assert message in error["message"]


@pytest.mark.parametrize(
    ("password", "code"),
    [
        ("corta12", "password_length"),
        ("x" * 65, "password_length"),
        ("Contrasena", "password_too_common"),
    ],
)
def test_contrasena_invalida_se_rechaza(
    db_client: TestClient, password: str, code: str
) -> None:
    response = db_client.post(REGISTER, json=_registration(password=password))

    assert response.status_code == 422
    assert response.json()["code"] == code


def test_is_superuser_se_rechaza(db_client: TestClient, migrated_db: str) -> None:
    response = db_client.post(REGISTER, json=_registration(is_superuser=True))

    assert response.status_code == 422
    assert response.json()["errors"][0]["field"] == "is_superuser"
    with psycopg.connect(migrated_db) as conn:
        assert conn.execute("SELECT count(*) FROM app_user").fetchone() == (0,)


# ─── HU-02 Verificar el correo ─────────────────────────────────────────────


def test_enlace_vigente_activa_la_cuenta(
    db_client: TestClient, outbox: FakeEmailSender, migrated_db: str
) -> None:
    db_client.post(REGISTER, json=_registration())

    response = db_client.post(VERIFY, json={"token": _token_from(outbox)})

    assert response.status_code == 204
    status, verified_at, _, _ = _user_row(migrated_db, "ana.rios")
    assert status == "active"
    assert verified_at is not None


def test_verificar_dos_veces_no_cambia_nada(
    db_client: TestClient, outbox: FakeEmailSender, migrated_db: str
) -> None:
    db_client.post(REGISTER, json=_registration())
    token = _token_from(outbox)
    db_client.post(VERIFY, json={"token": token})
    first = _user_row(migrated_db, "ana.rios")

    response = db_client.post(VERIFY, json={"token": token})

    assert response.status_code == 204
    assert _user_row(migrated_db, "ana.rios") == first


def test_enlace_vencido_se_rechaza(db_client: TestClient, migrated_db: str) -> None:
    user_id = uuid.UUID(db_client.post(REGISTER, json=_registration()).json()["id"])
    expired = create_email_token(
        user_id,
        TokenPurpose.VERIFY_EMAIL,
        timedelta(hours=24),
        SECRET_KEY,
        datetime.now(UTC) - timedelta(hours=25),
    )

    response = db_client.post(VERIFY, json={"token": expired})

    assert response.status_code == 400
    assert response.json()["code"] == "expired_token"
    assert _user_row(migrated_db, "ana.rios")[0] == "unverified"


def test_enlace_alterado_se_rechaza(
    db_client: TestClient, outbox: FakeEmailSender
) -> None:
    db_client.post(REGISTER, json=_registration())

    response = db_client.post(VERIFY, json={"token": _token_from(outbox) + "x"})

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_token"


def test_enlace_de_cuenta_que_no_existe_se_rechaza(db_client: TestClient) -> None:
    token = create_email_token(
        uuid.uuid4(),
        TokenPurpose.VERIFY_EMAIL,
        timedelta(hours=24),
        SECRET_KEY,
        datetime.now(UTC),
    )

    response = db_client.post(VERIFY, json={"token": token})

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_token"


def test_reenvio_manda_un_enlace_nuevo_que_sirve(
    db_client: TestClient, outbox: FakeEmailSender, migrated_db: str
) -> None:
    db_client.post(REGISTER, json=_registration())

    response = db_client.post(RESEND, json={"email": "ANA.rios@correo.com"})

    assert response.status_code == 202
    assert len(outbox.sent) == 2
    assert (
        db_client.post(VERIFY, json={"token": _token_from(outbox)}).status_code == 204
    )
    assert _user_row(migrated_db, "ana.rios")[0] == "active"


@pytest.mark.parametrize("verified", [True, False])
def test_reenvio_responde_igual_si_no_hay_nada_que_enviar(
    db_client: TestClient, outbox: FakeEmailSender, verified: bool
) -> None:
    db_client.post(REGISTER, json=_registration())
    if verified:
        db_client.post(VERIFY, json={"token": _token_from(outbox)})
        email = "ana.rios@correo.com"
    else:
        email = "nadie@correo.com"
    sent_before = len(outbox.sent)

    response = db_client.post(RESEND, json={"email": email})

    assert response.status_code == 202
    assert response.content == b""
    assert len(outbox.sent) == sent_before


def test_sexto_reenvio_en_un_minuto_se_rechaza(db_client: TestClient) -> None:
    for _ in range(5):
        assert db_client.post(RESEND, json={"email": "x@correo.com"}).status_code == 202

    response = db_client.post(RESEND, json={"email": "x@correo.com"})

    assert response.status_code == 429
    assert response.json()["code"] == "too_many_requests"
    assert int(response.headers["retry-after"]) > 0


class _BrokenEmailSender:
    def send(self, message: object) -> None:
        raise ConnectionRefusedError("SMTP apagado")


def test_si_el_correo_falla_la_cuenta_queda_y_se_puede_reenviar(
    db_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    db_client.app.state.email_sender = _BrokenEmailSender()

    response = db_client.post(REGISTER, json=_registration())

    assert response.status_code == 201
    assert "No se pudo enviar el correo" in caplog.text
    assert "token=" not in caplog.text
