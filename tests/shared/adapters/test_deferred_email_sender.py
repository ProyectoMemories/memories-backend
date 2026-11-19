"""Correos que se envían después de responder (D74)."""

import pytest

from app.shared.adapters.deferred_email_sender import DeferredEmailSender
from app.shared.use_cases.ports import EmailDeliveryError, EmailMessage
from tests.conftest import FakeEmailSender


def _message(to: str) -> EmailMessage:
    return EmailMessage(to=to, subject="Asunto", text="enlace?token=secreto")


class FailingOnceEmailSender(FakeEmailSender):
    """Falla con el primer correo y envía los demás."""

    def __init__(self) -> None:
        super().__init__()
        self.attempts = 0

    def send(self, message: EmailMessage) -> None:
        self.attempts += 1
        if self.attempts == 1:
            raise EmailDeliveryError("SMTP apagado")
        super().send(message)


def test_send_solo_guarda_el_correo() -> None:
    outbox = FakeEmailSender()
    deferred = DeferredEmailSender(outbox)

    deferred.send(_message("ana@correo.com"))

    assert outbox.sent == []


def test_flush_envia_en_orden_y_no_repite() -> None:
    outbox = FakeEmailSender()
    deferred = DeferredEmailSender(outbox)
    deferred.send(_message("ana@correo.com"))
    deferred.send(_message("luis@correo.com"))

    deferred.flush()
    deferred.flush()

    assert [message.to for message in outbox.sent] == [
        "ana@correo.com",
        "luis@correo.com",
    ]


def test_si_un_correo_falla_se_registra_sin_el_contenido_y_sigue(
    caplog: pytest.LogCaptureFixture,
) -> None:
    outbox = FailingOnceEmailSender()
    deferred = DeferredEmailSender(outbox)
    deferred.send(_message("ana@correo.com"))
    deferred.send(_message("luis@correo.com"))

    deferred.flush()

    assert [message.to for message in outbox.sent] == ["luis@correo.com"]
    assert "No se pudo enviar un correo" in caplog.text
    assert "token=" not in caplog.text
