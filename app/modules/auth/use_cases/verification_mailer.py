"""Correo con el enlace de verificación (HU-01, HU-02; RN-11, D65)."""

import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

from app.modules.auth.entities.user import User
from app.modules.auth.use_cases.ports import EmailLinkTokens, TokenPurpose
from app.shared.use_cases.ports import EmailDeliveryError, EmailMessage, EmailSender

VERIFY_EMAIL_LIFETIME = timedelta(hours=24)

logger = logging.getLogger(__name__)


class VerificationMailer:
    def __init__(
        self,
        email_sender: EmailSender,
        email_links: EmailLinkTokens,
        web_app_origin: str,
    ) -> None:
        self._email_sender = email_sender
        self._email_links = email_links
        # El enlace abre la pantalla /verify-email de la app web (D65).
        self._web_app_origin = web_app_origin

    def send(self, user: User, now: datetime) -> None:
        """Envía el enlace. Si falla, la cuenta queda y se puede pedir otro."""
        token = self._email_links.create(
            user.id, TokenPurpose.VERIFY_EMAIL, VERIFY_EMAIL_LIFETIME, now
        )
        try:
            self._email_sender.send(self._message(user, token))
        except EmailDeliveryError:
            # No se registra el enlace: contiene el token.
            logger.exception("No se pudo enviar el correo de verificación")

    def _message(self, user: User, token: str) -> EmailMessage:
        link = f"{self._web_app_origin}/verify-email?{urlencode({'token': token})}"
        return EmailMessage(
            to=user.email,
            subject="Confirma tu correo en Memories",
            text=(
                f"Hola, {user.first_name}:\n\n"
                "Para activar tu cuenta de Memories, abre este enlace:\n\n"
                f"{link}\n\n"
                "El enlace vence en 24 horas. Si no creaste esta cuenta, ignora "
                "este correo.\n"
            ),
        )
