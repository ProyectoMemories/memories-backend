"""Caso de uso: pedir el enlace para recuperar la contraseña (HU-06; RF-05)."""

from app.modules.auth.use_cases.password_reset_mailer import PasswordResetMailer
from app.modules.auth.use_cases.ports import UserGateway
from app.shared.entities.clock import Clock


class RequestPasswordReset:
    def __init__(
        self, users: UserGateway, mailer: PasswordResetMailer, clock: Clock
    ) -> None:
        self._users = users
        self._mailer = mailer
        self._clock = clock

    def execute(self, email: str) -> None:
        """Envía el enlace si la cuenta existe y puede recuperarse.

        Quien llama recibe siempre la misma respuesta, para no revelar qué
        correos tienen cuenta (specs/auth/design.md §6).
        """
        user = self._users.get_by_email(email)
        if user is not None and user.can_recover_password:
            self._mailer.send(user, self._clock())
