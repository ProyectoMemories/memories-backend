"""Correo con el enlace para crear una contraseña nueva (HU-06; D62-A)."""

import logging
from datetime import datetime, timedelta
from urllib.parse import urlencode

from app.modules.auth.entities.user import User
from app.modules.auth.use_cases.ports import PasswordResetTokens
from app.shared.use_cases.ports import EmailDeliveryError, EmailMessage, EmailSender

PASSWORD_RESET_LIFETIME = timedelta(minutes=30)

logger = logging.getLogger(__name__)


class PasswordResetMailer:
    def __init__(
        self,
        email_sender: EmailSender,
        reset_tokens: PasswordResetTokens,
        web_app_origin: str,
    ) -> None:
        self._email_sender = email_sender
        self._reset_tokens = reset_tokens
        # Abre la pantalla /reset-password de la app web, como /verify-email (D65).
        self._web_app_origin = web_app_origin

    def send(self, user: User, now: datetime) -> None:
        token = self._reset_tokens.create(
            user.id, user.password_changed_at, PASSWORD_RESET_LIFETIME, now
        )
        try:
            self._email_sender.send(self._message(user, token))
        except EmailDeliveryError:
            # No se registra el enlace: contiene el token.
            logger.exception("No se pudo enviar el correo de recuperación")

    def _message(self, user: User, token: str) -> EmailMessage:
        link = f"{self._web_app_origin}/reset-password?{urlencode({'token': token})}"
        return EmailMessage(
            to=user.email,
            subject="Crea una contraseña nueva en Memories",
            text=(
                f"Hola, {user.first_name}:\n\n"
                "Para crear una contraseña nueva, abre este enlace:\n\n"
                f"{link}\n\n"
                "El enlace vence en 30 minutos y sirve una sola vez. Si no lo "
                "pediste, ignora este correo: tu contraseña no cambia.\n"
            ),
        )
