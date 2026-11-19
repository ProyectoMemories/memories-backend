"""EmailSender que envía los correos después de responder (D74).

Si un correo se enviara dentro de la petición, la respuesta tardaría más cuando
la cuenta existe y eso revelaría qué correos tienen cuenta. Este adaptador
cumple el mismo puerto, pero solo guarda el correo; `flush()` lo envía cuando la
respuesta ya salió (lo programa `open_request_scope` en `app/main.py`).
"""

import logging

from app.shared.use_cases.ports import EmailDeliveryError, EmailMessage, EmailSender

logger = logging.getLogger(__name__)


class DeferredEmailSender:
    def __init__(self, email_sender: EmailSender) -> None:
        self._email_sender = email_sender
        self._pending: list[EmailMessage] = []

    def send(self, message: EmailMessage) -> None:
        self._pending.append(message)

    def flush(self) -> None:
        """Envía lo pendiente. Un fallo no detiene a los demás ni se reintenta."""
        pending, self._pending = self._pending, []
        for message in pending:
            try:
                self._email_sender.send(message)
            except EmailDeliveryError:
                # No se registra el correo: lleva el enlace con el token.
                logger.exception("No se pudo enviar un correo en segundo plano")
