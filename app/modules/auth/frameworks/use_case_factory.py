"""Interactores de auth para una petición, sobre su sesión de base de datos."""

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.modules.auth.adapters.gateways.session_gateway import SqlSessionGateway
from app.modules.auth.adapters.gateways.user_gateway import SqlUserGateway
from app.modules.auth.use_cases.authenticate import Authenticate
from app.modules.auth.use_cases.change_password import ChangePassword
from app.modules.auth.use_cases.log_in import LogIn
from app.modules.auth.use_cases.log_out import LogOut
from app.modules.auth.use_cases.password_reset_mailer import PasswordResetMailer
from app.modules.auth.use_cases.refresh_session import RefreshSession
from app.modules.auth.use_cases.register_user import RegisterUser
from app.modules.auth.use_cases.request_password_reset import RequestPasswordReset
from app.modules.auth.use_cases.resend_verification import ResendVerification
from app.modules.auth.use_cases.reset_password import ResetPassword
from app.modules.auth.use_cases.verification_mailer import VerificationMailer
from app.modules.auth.use_cases.verify_email import VerifyEmail
from app.shared.adapters.sql_unit_of_work import SqlUnitOfWork
from app.shared.use_cases.ports import EmailSender

if TYPE_CHECKING:
    # Solo para los tipos: composition.py importa este archivo.
    from app.modules.auth.frameworks.composition import AuthModule


class AuthUseCaseFactory:
    """Interactores de una petición. Implementa AuthUseCases (adapters/controllers)."""

    def __init__(
        self, module: "AuthModule", session: Session, deferred_email: EmailSender
    ) -> None:
        self._module = module
        # forgot y resend envían con este, después de responder, para no
        # revelar por el tiempo qué cuentas existen (D74).
        self._deferred_email = deferred_email
        self._users = SqlUserGateway(session)
        self._sessions = SqlSessionGateway(session)
        self._unit_of_work = SqlUnitOfWork(session)

    def register_user(self) -> RegisterUser:
        module = self._module
        return RegisterUser(
            self._users,
            self._unit_of_work,
            module.hasher,
            module.password_policy,
            module.mailer,
            module.privacy_policy_version,
            module.clock,
        )

    def verify_email(self) -> VerifyEmail:
        module = self._module
        return VerifyEmail(
            self._users, self._unit_of_work, module.email_links, module.clock
        )

    def resend_verification(self) -> ResendVerification:
        module = self._module
        mailer = VerificationMailer(
            self._deferred_email, module.email_links, module.web_app_origin
        )
        return ResendVerification(self._users, mailer, module.clock)

    def log_in(self) -> LogIn:
        module = self._module
        return LogIn(
            self._users,
            self._sessions,
            self._unit_of_work,
            module.hasher,
            module.refresh_secrets,
            module.token_issuer,
            module.clock,
        )

    def refresh_session(self) -> RefreshSession:
        module = self._module
        return RefreshSession(
            self._users,
            self._sessions,
            self._unit_of_work,
            module.refresh_secrets,
            module.token_issuer,
            module.clock,
        )

    def log_out(self) -> LogOut:
        module = self._module
        return LogOut(
            self._sessions, self._unit_of_work, module.refresh_secrets, module.clock
        )

    def authenticate(self) -> Authenticate:
        module = self._module
        return Authenticate(
            self._users, self._sessions, module.access_tokens, module.clock
        )

    def request_password_reset(self) -> RequestPasswordReset:
        module = self._module
        mailer = PasswordResetMailer(
            self._deferred_email, module.reset_tokens, module.web_app_origin
        )
        return RequestPasswordReset(self._users, mailer, module.clock)

    def reset_password(self) -> ResetPassword:
        module = self._module
        return ResetPassword(
            self._users,
            self._sessions,
            self._unit_of_work,
            module.hasher,
            module.password_policy,
            module.reset_tokens,
            module.clock,
        )

    def change_password(self) -> ChangePassword:
        module = self._module
        return ChangePassword(
            self._users,
            self._sessions,
            self._unit_of_work,
            module.hasher,
            module.password_policy,
            module.clock,
        )
