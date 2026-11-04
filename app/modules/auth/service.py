"""Reglas de negocio de auth: registro y verificación del correo (HU-01, HU-02).

No importa FastAPI (CLAUDE.md §7): recibe datos ya validados y lanza AppError.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from urllib.parse import urlencode

from app.db import UniqueViolationError, new_id
from app.email import EmailMessage, EmailSender
from app.errors import AppError
from app.modules.auth import tokens
from app.modules.auth.models import AccountStatus, AppUser, PrivacyConsent
from app.modules.auth.passwords import (
    MAX_LENGTH,
    MIN_LENGTH,
    PasswordHasher,
    password_problem,
)
from app.modules.auth.repository import AuthRepository
from app.modules.auth.tokens import TokenPurpose

logger = logging.getLogger(__name__)

MIN_AGE_YEARS = 14  # RN-08
VERIFY_EMAIL_LIFETIME = timedelta(hours=24)  # RN-11


# ─── Errores ───────────────────────────────────────────────────────────────


class UnderageError(AppError):
    status_code = 422
    code = "underage"
    message = f"Necesitas tener al menos {MIN_AGE_YEARS} años para registrarte."


class PrivacyPolicyNotAcceptedError(AppError):
    status_code = 422
    code = "privacy_policy_not_accepted"
    message = "Debes aceptar la política de privacidad para registrarte."


class PasswordLengthError(AppError):
    status_code = 422
    code = "password_length"
    message = f"La contraseña debe tener entre {MIN_LENGTH} y {MAX_LENGTH} caracteres."


class PasswordTooCommonError(AppError):
    status_code = 422
    code = "password_too_common"
    message = "Esa contraseña es muy común. Elige otra."


class UsernameTakenError(AppError):
    status_code = 409
    code = "username_taken"
    message = "Ese nombre de usuario ya está en uso."


class EmailTakenError(AppError):
    status_code = 409
    code = "email_taken"
    message = "Ya existe una cuenta con ese correo."


class ExpiredTokenError(AppError):
    code = "expired_token"
    message = "El enlace venció. Pide uno nuevo."


class InvalidTokenError(AppError):
    code = "invalid_token"
    message = "El enlace no es válido. Pide uno nuevo."


_PASSWORD_ERRORS: dict[str, type[AppError]] = {
    "length": PasswordLengthError,
    "common": PasswordTooCommonError,
}
_UNIQUE_ERRORS: dict[str, type[AppError]] = {
    "uq_app_user_username_ci": UsernameTakenError,
    "uq_app_user_email_ci": EmailTakenError,
}


# ─── Datos de entrada ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class Registration:
    username: str
    email: str
    password: str
    first_name: str
    paternal_surname: str
    maternal_surname: str | None
    birth_date: date
    accepts_privacy_policy: bool


@dataclass(frozen=True)
class AuthConfig:
    secret_key: str
    privacy_policy_version: str
    # Los enlaces de los correos abren la app web.
    web_app_origin: str


def utc_now() -> datetime:
    return datetime.now(UTC)


def age_on(birth_date: date, today: date) -> int:
    had_birthday = (today.month, today.day) >= (birth_date.month, birth_date.day)
    return today.year - birth_date.year - (0 if had_birthday else 1)


# ─── Servicio ──────────────────────────────────────────────────────────────


class AuthService:
    def __init__(
        self,
        repository: AuthRepository,
        hasher: PasswordHasher,
        email_sender: EmailSender,
        config: AuthConfig,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._repository = repository
        self._hasher = hasher
        self._email_sender = email_sender
        self._config = config
        self._clock = clock

    def register(self, data: Registration) -> AppUser:
        """Crea la cuenta sin verificar y envía el enlace (HU-01)."""
        now = self._clock()
        if not data.accepts_privacy_policy:
            raise PrivacyPolicyNotAcceptedError
        if age_on(data.birth_date, now.date()) < MIN_AGE_YEARS:
            raise UnderageError
        self._check_password(data.password)

        user = AppUser(
            id=new_id(),
            username=data.username,
            email=data.email,
            password_hash=self._hasher.hash(data.password),
            first_name=data.first_name,
            paternal_surname=data.paternal_surname,
            maternal_surname=data.maternal_surname,
            birth_date=data.birth_date,
            status=AccountStatus.UNVERIFIED,  # RN-12
        )
        consent = PrivacyConsent(
            id=new_id(),
            user_id=user.id,
            policy_version=self._config.privacy_policy_version,
            accepted_at=now,
        )
        try:
            self._repository.add_user(user, consent)
        except UniqueViolationError as error:
            raise _UNIQUE_ERRORS[error.constraint]() from error
        self._repository.commit()

        self._send_verification_email(user, now)
        return user

    def verify_email(self, token: str) -> None:
        """Activa la cuenta. Verificar dos veces no cambia nada (HU-02)."""
        try:
            user_id = tokens.read_email_token(
                token, TokenPurpose.VERIFY_EMAIL, self._config.secret_key
            )
        except tokens.ExpiredTokenError as error:
            raise ExpiredTokenError from error
        except tokens.InvalidTokenError as error:
            raise InvalidTokenError from error

        user = self._repository.get_user(user_id)
        if user is None:
            # Firma válida pero la cuenta ya no existe (por ejemplo, se eliminó).
            raise InvalidTokenError
        if user.status is not AccountStatus.UNVERIFIED:
            return
        user.status = AccountStatus.ACTIVE
        user.email_verified_at = self._clock()
        self._repository.commit()

    def resend_verification(self, email: str) -> None:
        """Reenvía el enlace si la cuenta existe y no está verificada.

        Quien llama recibe siempre la misma respuesta, para no revelar qué
        correos tienen cuenta (specs/auth/design.md §6).
        """
        user = self._repository.get_user_by_email(email)
        if user is None or user.status is not AccountStatus.UNVERIFIED:
            return
        self._send_verification_email(user, self._clock())

    def _check_password(self, password: str) -> None:
        problem = password_problem(password)
        if problem is not None:
            raise _PASSWORD_ERRORS[problem]

    def _send_verification_email(self, user: AppUser, now: datetime) -> None:
        token = tokens.create_email_token(
            user.id,
            TokenPurpose.VERIFY_EMAIL,
            VERIFY_EMAIL_LIFETIME,
            self._config.secret_key,
            now,
        )
        link = (
            f"{self._config.web_app_origin}/verify-email?{urlencode({'token': token})}"
        )
        message = EmailMessage(
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
        try:
            self._email_sender.send(message)
        except OSError:
            # La cuenta ya quedó guardada; la persona puede pedir otro enlace.
            # No se registra el enlace: contiene el token.
            logger.exception("No se pudo enviar el correo de verificación")
