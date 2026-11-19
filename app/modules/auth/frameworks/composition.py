"""Composición de auth: conecta cada puerto con su adaptador.

`AuthModule` crea una sola vez lo que no tiene estado por petición (hash,
tokens, lista de contraseñas). `AuthModule.use_cases(session)` arma, para una
petición, los interactores con gateways sobre esa sesión de base de datos.
"""

from sqlalchemy.orm import Session

from app.modules.auth.adapters.gateways.session_gateway import SqlSessionGateway
from app.modules.auth.adapters.gateways.user_gateway import SqlUserGateway
from app.modules.auth.adapters.services.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from app.modules.auth.adapters.services.common_passwords import load_common_passwords
from app.modules.auth.adapters.services.jwt_tokens import (
    JwtAccessTokens,
    JwtEmailLinkTokens,
)
from app.modules.auth.adapters.services.sha256_refresh_secrets import (
    Sha256RefreshSecrets,
)
from app.modules.auth.entities.password_policy import PasswordPolicy
from app.modules.auth.use_cases.authenticate import Authenticate
from app.modules.auth.use_cases.log_in import LogIn
from app.modules.auth.use_cases.log_out import LogOut
from app.modules.auth.use_cases.refresh_session import RefreshSession
from app.modules.auth.use_cases.register_user import RegisterUser
from app.modules.auth.use_cases.resend_verification import ResendVerification
from app.modules.auth.use_cases.token_issuer import TokenIssuer
from app.modules.auth.use_cases.verification_mailer import VerificationMailer
from app.modules.auth.use_cases.verify_email import VerifyEmail
from app.shared.adapters.sql_unit_of_work import SqlUnitOfWork
from app.shared.entities.clock import Clock, utc_now
from app.shared.frameworks.config import Settings
from app.shared.use_cases.ports import EmailSender


class AuthModule:
    def __init__(
        self, settings: Settings, email_sender: EmailSender, clock: Clock = utc_now
    ) -> None:
        self.clock = clock
        self.privacy_policy_version = settings.privacy_policy_version
        self.hasher = Argon2PasswordHasher()
        self.password_policy = PasswordPolicy(load_common_passwords())
        self.refresh_secrets = Sha256RefreshSecrets()
        self.access_tokens = JwtAccessTokens(settings.secret_key)
        self.token_issuer = TokenIssuer(self.access_tokens)
        self.email_links = JwtEmailLinkTokens(settings.secret_key)
        self.mailer = VerificationMailer(
            email_sender, self.email_links, settings.web_app_origin
        )

    def use_cases(self, session: Session) -> "AuthUseCaseFactory":
        return AuthUseCaseFactory(self, session)


class AuthUseCaseFactory:
    """Interactores de una petición. Implementa AuthUseCases (adapters/controllers)."""

    def __init__(self, module: AuthModule, session: Session) -> None:
        self._module = module
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
        return ResendVerification(self._users, self._module.mailer, self._module.clock)

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
