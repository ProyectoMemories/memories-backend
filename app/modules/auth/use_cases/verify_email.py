"""Caso de uso: verificar el correo con el enlace (HU-02; RN-11)."""

from app.modules.auth.use_cases.errors import ExpiredLinkError, InvalidLinkError
from app.modules.auth.use_cases.ports import (
    EmailLinkTokens,
    TokenExpiredError,
    TokenInvalidError,
    TokenPurpose,
    UserGateway,
)
from app.shared.entities.clock import Clock
from app.shared.use_cases.ports import UnitOfWork


class VerifyEmail:
    def __init__(
        self,
        users: UserGateway,
        unit_of_work: UnitOfWork,
        email_links: EmailLinkTokens,
        clock: Clock,
    ) -> None:
        self._users = users
        self._unit_of_work = unit_of_work
        self._email_links = email_links
        self._clock = clock

    def execute(self, token: str) -> None:
        """Activa la cuenta. Verificar dos veces no cambia nada."""
        try:
            user_id = self._email_links.read(token, TokenPurpose.VERIFY_EMAIL)
        except TokenExpiredError as error:
            raise ExpiredLinkError from error
        except TokenInvalidError as error:
            raise InvalidLinkError from error

        user = self._users.get(user_id)
        if user is None:
            # Firma válida pero la cuenta ya no existe (por ejemplo, se eliminó).
            raise InvalidLinkError
        if user.verify_email(self._clock()):
            self._users.save(user)
            self._unit_of_work.commit()
