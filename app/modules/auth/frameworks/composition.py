"""Composición de auth: conecta cada puerto con su adaptador.

`AuthModule` crea una sola vez lo que no tiene estado por petición (hash,
tokens, lista de contraseñas). `AuthModule.use_cases(session)` arma, para una
petición, los interactores con gateways sobre esa sesión de base de datos.
"""

from sqlalchemy.orm import Session

from app.modules.auth.adapters.services.argon2_password_hasher import (
    Argon2PasswordHasher,
)
from app.modules.auth.adapters.services.common_passwords import load_common_passwords
from app.modules.auth.adapters.services.jwt_tokens import (
    JwtAccessTokens,
    JwtEmailLinkTokens,
    JwtPasswordResetTokens,
)
from app.modules.auth.adapters.services.sha256_refresh_secrets import (
    Sha256RefreshSecrets,
)
from app.modules.auth.entities.password_policy import PasswordPolicy
from app.modules.auth.frameworks.use_case_factory import AuthUseCaseFactory
from app.modules.auth.use_cases.token_issuer import TokenIssuer
from app.modules.auth.use_cases.verification_mailer import VerificationMailer
from app.shared.entities.clock import Clock, utc_now
from app.shared.frameworks.config import Settings
from app.shared.use_cases.ports import EmailSender


class AuthModule:
    def __init__(
        self, settings: Settings, email_sender: EmailSender, clock: Clock = utc_now
    ) -> None:
        self.clock = clock
        self.privacy_policy_version = settings.privacy_policy_version
        self.web_app_origin = settings.web_app_origin
        self.hasher = Argon2PasswordHasher()
        self.password_policy = PasswordPolicy(load_common_passwords())
        self.refresh_secrets = Sha256RefreshSecrets()
        self.access_tokens = JwtAccessTokens(settings.secret_key)
        self.token_issuer = TokenIssuer(self.access_tokens)
        self.email_links = JwtEmailLinkTokens(settings.secret_key)
        self.mailer = VerificationMailer(
            email_sender, self.email_links, settings.web_app_origin
        )
        self.reset_tokens = JwtPasswordResetTokens(settings.secret_key)

    def use_cases(
        self, session: Session, deferred_email: EmailSender
    ) -> AuthUseCaseFactory:
        """`deferred_email` envía después de responder (D74)."""
        return AuthUseCaseFactory(self, session, deferred_email)
