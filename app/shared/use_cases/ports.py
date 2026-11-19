"""Puertos que comparten los casos de uso de todos los módulos."""

from dataclasses import dataclass
from typing import Protocol


class UnitOfWork(Protocol):
    """Confirma de una vez todo lo que hizo un caso de uso."""

    def commit(self) -> None: ...


@dataclass(frozen=True)
class EmailMessage:
    to: str
    subject: str
    text: str


class EmailDeliveryError(Exception):
    """El correo no salió (servidor caído, rechazado…)."""


class EmailSender(Protocol):
    def send(self, message: EmailMessage) -> None:
        """Envía el correo o lanza EmailDeliveryError."""
        ...
