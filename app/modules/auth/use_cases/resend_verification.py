"""Caso de uso: reenviar el enlace de verificación (HU-02)."""

from app.modules.auth.use_cases.ports import UserGateway
from app.modules.auth.use_cases.verification_mailer import VerificationMailer
from app.shared.entities.clock import Clock


class ResendVerification:
    def __init__(
        self, users: UserGateway, mailer: VerificationMailer, clock: Clock
    ) -> None:
        self._users = users
        self._mailer = mailer
        self._clock = clock

    def execute(self, email: str) -> None:
        """Reenvía solo si la cuenta existe y no está verificada.

        Quien llama recibe siempre la misma respuesta, para no revelar qué
        correos tienen cuenta (specs/auth/design.md §6).
        """
        user = self._users.get_by_email(email)
        if user is not None and user.is_unverified:
            self._mailer.send(user, self._clock())
