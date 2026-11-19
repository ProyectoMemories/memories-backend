"""Correos de forgot y resend después de responder; register, dentro (D74).

TestClient espera a que terminen las tareas en segundo plano antes de devolver
la respuesta, así que no muestra el orden. Por eso se llama a la app por ASGI
directo y se anota cuándo sale la respuesta y cuándo el correo.
"""

import asyncio
import json
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.types import Message

from app.shared.use_cases.ports import EmailMessage
from tests.conftest import FakeEmailSender

AUTH = "/api/v1/auth"
REGISTRATION = {
    "username": "ana.rios",
    "email": "ana@correo.com",
    "password": "caballo bateria grapa",
    "first_name": "Ana",
    "paternal_surname": "Ríos",
    "birth_date": "2000-05-17",
    "accepts_privacy_policy": True,
}
DEFERRED_ENDPOINTS = ["/password/forgot", "/verify-email/resend"]


def _post(app: FastAPI, path: str, body: dict[str, Any], events: list[str]) -> int:
    """POST por ASGI; anota "response" cuando sale el último trozo del cuerpo."""
    payload = json.dumps(body).encode()
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": f"{AUTH}{path}",
        "raw_path": f"{AUTH}{path}".encode(),
        "root_path": "",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 50000),
        "server": ("testserver", 80),
    }
    status = 0

    async def receive() -> Message:
        return {"type": "http.request", "body": payload, "more_body": False}

    async def send(message: Message) -> None:
        nonlocal status
        if message["type"] == "http.response.start":
            status = message["status"]
        elif message["type"] == "http.response.body" and not message.get("more_body"):
            events.append("response")

    asyncio.run(app(scope, receive, send))
    return status


@pytest.fixture
def events(outbox: FakeEmailSender, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Orden en que salen la respuesta y los correos."""
    recorded: list[str] = []
    send_email = outbox.send

    def record_and_send(message: EmailMessage) -> None:
        recorded.append("email")
        send_email(message)

    monkeypatch.setattr(outbox, "send", record_and_send)
    return recorded


@pytest.fixture
def app(db_client: TestClient) -> FastAPI:
    application: FastAPI = db_client.app  # type: ignore[assignment]
    return application


def test_register_envia_el_correo_antes_de_responder(
    app: FastAPI, events: list[str]
) -> None:
    assert _post(app, "/register", REGISTRATION, events) == 201
    assert events == ["email", "response"]


@pytest.mark.parametrize("path", DEFERRED_ENDPOINTS)
def test_el_correo_sale_despues_de_la_respuesta(
    app: FastAPI, db_client: TestClient, events: list[str], path: str
) -> None:
    db_client.post(f"{AUTH}/register", json=REGISTRATION)
    events.clear()

    assert _post(app, path, {"email": "ana@correo.com"}, events) == 202
    assert events == ["response", "email"]


@pytest.mark.parametrize("path", DEFERRED_ENDPOINTS)
def test_mientras_se_envia_el_correo_no_ocupa_una_conexion_a_la_base(
    app: FastAPI,
    db_client: TestClient,
    outbox: FakeEmailSender,
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    """Un SMTP lento no debe dejar a la API sin conexiones."""
    db_client.post(f"{AUTH}/register", json=REGISTRATION)
    pool = app.state.sessionmaker.kw["bind"].pool
    connections_in_use: list[int] = []
    send_email = outbox.send

    def record_and_send(message: EmailMessage) -> None:
        connections_in_use.append(pool.checkedout())
        send_email(message)

    monkeypatch.setattr(outbox, "send", record_and_send)

    db_client.post(f"{AUTH}{path}", json={"email": "ana@correo.com"})

    assert connections_in_use == [0]


@pytest.mark.parametrize("path", DEFERRED_ENDPOINTS)
def test_con_el_smtp_caido_responde_igual_y_lo_registra(
    db_client: TestClient,
    outbox: FakeEmailSender,
    caplog: pytest.LogCaptureFixture,
    path: str,
) -> None:
    db_client.post(f"{AUTH}/register", json=REGISTRATION)
    outbox.failing = True

    response = db_client.post(f"{AUTH}{path}", json={"email": "ana@correo.com"})

    assert response.status_code == 202
    assert "No se pudo enviar un correo en segundo plano" in caplog.text
    assert "token=" not in caplog.text
