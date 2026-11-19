"""Arma cada interactor de auth con dobles en memoria."""

from dataclasses import dataclass, field
from datetime import date, timedelta

import pytest

from app.modules.auth.entities.password_policy import PasswordPolicy
from app.modules.auth.entities.user import AccountStatus, User
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
from app.modules.auth.use_cases.token_issuer import TokenIssuer
from app.modules.auth.use_cases.verification_mailer import VerificationMailer
from app.modules.auth.use_cases.verify_email import VerifyEmail
from tests.conftest import FakeEmailSender
from tests.modules.auth.use_cases.fakes import (
    FakeAccessTokens,
    FakeClock,
    FakeEmailLinkTokens,
    FakePasswordHasher,
    FakePasswordResetTokens,
    FakeRefreshSecrets,
    FakeUnitOfWork,
    InMemorySessionGateway,
    InMemoryUserGateway,
)

PASSWORD = "caballo bateria grapa"


@dataclass
class AuthKit:
    clock: FakeClock = field(default_factory=FakeClock)
    users: InMemoryUserGateway = field(default_factory=InMemoryUserGateway)
    sessions: InMemorySessionGateway = field(default_factory=InMemorySessionGateway)
    unit_of_work: FakeUnitOfWork = field(default_factory=FakeUnitOfWork)
    hasher: FakePasswordHasher = field(default_factory=FakePasswordHasher)
    secrets: FakeRefreshSecrets = field(default_factory=FakeRefreshSecrets)
    outbox: FakeEmailSender = field(default_factory=FakeEmailSender)

    def __post_init__(self) -> None:
        self.access_tokens = FakeAccessTokens(self.clock)
        self.email_links = FakeEmailLinkTokens(self.clock)
        self.issuer = TokenIssuer(self.access_tokens)
        self.mailer = VerificationMailer(
            self.outbox, self.email_links, "http://localhost:3000"
        )
        self.reset_tokens = FakePasswordResetTokens(self.clock)
        self.reset_mailer = PasswordResetMailer(
            self.outbox, self.reset_tokens, "http://localhost:3000"
        )

    def add_user(
        self, status: AccountStatus = AccountStatus.ACTIVE, username: str = "ana.rios"
    ) -> User:
        user = User.register(
            username=username,
            email=f"{username}@correo.com",
            password_hash=self.hasher.hash(PASSWORD),
            first_name="Ana",
            paternal_surname="Ríos",
            maternal_surname=None,
            birth_date=date(2000, 5, 17),
        )
        user.status = status
        # En la base la pone DEFAULT now() al crear la cuenta.
        user.password_changed_at = self.clock() - timedelta(days=10)
        self.users.save(user)
        return user

    def register_user(self) -> RegisterUser:
        policy = PasswordPolicy({"password"})
        return RegisterUser(
            self.users,
            self.unit_of_work,
            self.hasher,
            policy,
            self.mailer,
            "2026-11",
            self.clock,
        )

    def verify_email(self) -> VerifyEmail:
        return VerifyEmail(self.users, self.unit_of_work, self.email_links, self.clock)

    def resend_verification(self) -> ResendVerification:
        return ResendVerification(self.users, self.mailer, self.clock)

    def log_in(self) -> LogIn:
        return LogIn(
            self.users,
            self.sessions,
            self.unit_of_work,
            self.hasher,
            self.secrets,
            self.issuer,
            self.clock,
        )

    def refresh_session(self) -> RefreshSession:
        return RefreshSession(
            self.users,
            self.sessions,
            self.unit_of_work,
            self.secrets,
            self.issuer,
            self.clock,
        )

    def log_out(self) -> LogOut:
        return LogOut(self.sessions, self.unit_of_work, self.secrets, self.clock)

    def authenticate(self) -> Authenticate:
        return Authenticate(self.users, self.sessions, self.access_tokens, self.clock)

    def request_password_reset(self) -> RequestPasswordReset:
        return RequestPasswordReset(self.users, self.reset_mailer, self.clock)

    def reset_password(self) -> ResetPassword:
        return ResetPassword(
            self.users,
            self.sessions,
            self.unit_of_work,
            self.hasher,
            PasswordPolicy({"password"}),
            self.reset_tokens,
            self.clock,
        )

    def change_password(self) -> ChangePassword:
        return ChangePassword(
            self.users,
            self.sessions,
            self.unit_of_work,
            self.hasher,
            PasswordPolicy({"password"}),
            self.clock,
        )


@pytest.fixture
def kit() -> AuthKit:
    return AuthKit()
