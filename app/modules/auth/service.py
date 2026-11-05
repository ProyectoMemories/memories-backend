"""Reglas de negocio de auth: registro, verificación y sesiones (HU-01 a HU-05).

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
from app.modules.auth.models import (
    AccountStatus,
    AppUser,
    ClientPlatform,
    PrivacyConsent,
    UserSession,
)
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
ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)  # D56
SESSION_LIFETIME = timedelta(days=30)  # D56, RN-67
DELETION_GRACE_PERIOD = timedelta(days=30)  # RN-14


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


class InvalidCredentialsError(AppError):
    status_code = 401
    code = "invalid_credentials"
    # Igual exista o no la cuenta (design.md §6).
    message = "El usuario o la contraseña no son correctos."


class EmailNotVerifiedError(AppError):
    status_code = 403
    code = "email_not_verified"
    message = "Verifica tu correo para entrar. Puedes pedir otro enlace."


class AccountSuspendedError(AppError):
    status_code = 403
    code = "account_suspended"
    message = "Tu cuenta está suspendida."


class InvalidRefreshTokenError(AppError):
    status_code = 401
    code = "invalid_refresh_token"
    message = "Tu sesión terminó. Vuelve a iniciar sesión."


class NotAuthenticatedError(AppError):
    status_code = 401
    code = "not_authenticated"
    message = "Necesitas iniciar sesión."
    default_headers = {"WWW-Authenticate": "Bearer"}


class AccessTokenExpiredError(NotAuthenticatedError):
    # La app renueva el token solo con este código (design.md §2).
    code = "access_token_expired"
    message = "Tu token de acceso venció."


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
class Login:
    identifier: str
    password: str
    platform: ClientPlatform
    device_name: str | None


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    expires_in: int  # segundos
    refresh_token: str
    platform: ClientPlatform


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

    def login(self, data: Login) -> IssuedTokens:
        """Abre una sesión para este dispositivo (HU-03, RN-67)."""
        now = self._clock()
        user = self._repository.get_user_by_login(data.identifier)
        if user is None:
            self._hasher.verify_dummy(data.password)
            raise InvalidCredentialsError

        valid, new_hash = self._hasher.verify_and_update(
            data.password, user.password_hash
        )
        if not valid:
            raise InvalidCredentialsError
        # Desde aquí la contraseña es correcta: se puede decir por qué no entra
        # (D62-E).
        self._allow_login(user, now)
        if new_hash is not None:
            user.password_hash = new_hash

        secret = tokens.new_refresh_secret()
        user_session = UserSession(
            id=new_id(),
            user_id=user.id,
            refresh_token_hash=tokens.hash_refresh_secret(secret),
            platform=data.platform,
            device_name=data.device_name,
            created_at=now,
            last_used_at=now,
            expires_at=now + SESSION_LIFETIME,
        )
        self._repository.add_session(user_session)
        self._repository.commit()
        return self._issue(user_session, secret, now)

    def refresh(
        self, refresh_token: str | None, platform: ClientPlatform
    ) -> IssuedTokens:
        """Rota el token de renovación (HU-04, RN-67)."""
        now = self._clock()
        if refresh_token is None:
            raise InvalidRefreshTokenError
        try:
            session_id, secret = tokens.parse_refresh_token(refresh_token)
        except tokens.InvalidTokenError as error:
            raise InvalidRefreshTokenError from error

        user_session = self._repository.get_session_for_update(session_id)
        if user_session is None or not _is_usable(user_session, platform, now):
            raise InvalidRefreshTokenError
        if not tokens.refresh_secret_matches(secret, user_session.refresh_token_hash):
            # El secreto ya se rotó: alguien usa un token viejo, quizá robado.
            user_session.revoked_at = now
            self._repository.commit()
            raise InvalidRefreshTokenError

        user = self._repository.get_user(user_session.user_id)
        if user is None or user.status is not AccountStatus.ACTIVE:
            raise InvalidRefreshTokenError

        new_secret = tokens.new_refresh_secret()
        user_session.refresh_token_hash = tokens.hash_refresh_secret(new_secret)
        user_session.last_used_at = now
        user_session.expires_at = now + SESSION_LIFETIME
        self._repository.commit()
        return self._issue(user_session, new_secret, now)

    def logout(self, refresh_token: str | None, platform: ClientPlatform) -> None:
        """Revoca la sesión de este dispositivo. Repetirlo no da error (HU-05)."""
        if refresh_token is None:
            return
        try:
            session_id, secret = tokens.parse_refresh_token(refresh_token)
        except tokens.InvalidTokenError:
            return  # No hay sesión que cerrar: el cliente igual borra sus tokens.

        now = self._clock()
        user_session = self._repository.get_session_for_update(session_id)
        if (
            user_session is not None
            and _is_usable(user_session, platform, now)
            and tokens.refresh_secret_matches(secret, user_session.refresh_token_hash)
        ):
            user_session.revoked_at = now
            self._repository.commit()

    def authenticate(self, access_token: str) -> AppUser:
        """Usuario del token de acceso (RN-67).

        Exige que la cuenta siga activa y que su sesión siga abierta: así cerrar
        sesión o cambiar la contraseña corta también el token de acceso (D56).
        """
        try:
            user_id, session_id = tokens.read_access_token(
                access_token, self._config.secret_key
            )
        except tokens.ExpiredTokenError as error:
            raise AccessTokenExpiredError from error
        except tokens.InvalidTokenError as error:
            raise NotAuthenticatedError from error

        user_session = self._repository.get_session(session_id)
        if (
            user_session is None
            or user_session.user_id != user_id
            or not _is_open(user_session, self._clock())
        ):
            raise NotAuthenticatedError
        user = self._repository.get_user(user_id)
        if user is None or user.status is not AccountStatus.ACTIVE:
            raise NotAuthenticatedError
        return user

    def _allow_login(self, user: AppUser, now: datetime) -> None:
        match user.status:
            case AccountStatus.UNVERIFIED:
                raise EmailNotVerifiedError  # RN-11
            case AccountStatus.SUSPENDED:
                raise AccountSuspendedError  # RN-17
            case AccountStatus.DEACTIVATED:
                user.status = AccountStatus.ACTIVE  # RN-68
            case AccountStatus.PENDING_DELETION:
                requested_at = user.deletion_requested_at
                if requested_at and now - requested_at >= DELETION_GRACE_PERIOD:
                    # Ya venció el plazo; solo falta que la borre la purga diaria.
                    raise InvalidCredentialsError
                user.status = AccountStatus.ACTIVE  # RN-14: se cancela
                user.deletion_requested_at = None
            case AccountStatus.ACTIVE:
                pass

    def _issue(
        self, user_session: UserSession, secret: str, now: datetime
    ) -> IssuedTokens:
        access_token = tokens.create_access_token(
            user_session.user_id,
            user_session.id,
            ACCESS_TOKEN_LIFETIME,
            self._config.secret_key,
            now,
        )
        return IssuedTokens(
            access_token=access_token,
            expires_in=int(ACCESS_TOKEN_LIFETIME.total_seconds()),
            refresh_token=tokens.format_refresh_token(user_session.id, secret),
            platform=user_session.platform,
        )

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


def _is_usable(
    user_session: UserSession, platform: ClientPlatform, now: datetime
) -> bool:
    """Sesión abierta y usada por el mismo canal en que se abrió."""
    return _is_open(user_session, now) and user_session.platform is platform


def _is_open(user_session: UserSession, now: datetime) -> bool:
    """Ni revocada ni vencida."""
    return user_session.revoked_at is None and user_session.expires_at > now
