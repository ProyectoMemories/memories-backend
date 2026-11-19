"""Caso de uso: registrarse (HU-01; RN-07 a RN-12, RN-50, D28, D65)."""

import uuid
from dataclasses import dataclass
from datetime import date

from app.modules.auth.entities.age_policy import ensure_minimum_age
from app.modules.auth.entities.password_policy import PasswordPolicy
from app.modules.auth.entities.privacy_consent import (
    PrivacyConsent,
    ensure_policy_accepted,
)
from app.modules.auth.entities.user import AccountStatus, User
from app.modules.auth.use_cases.ports import PasswordHasher, UserGateway
from app.modules.auth.use_cases.verification_mailer import VerificationMailer
from app.shared.entities.clock import Clock
from app.shared.use_cases.ports import UnitOfWork


@dataclass(frozen=True)
class RegisterUserInput:
    username: str
    email: str
    password: str
    first_name: str
    paternal_surname: str
    maternal_surname: str | None
    birth_date: date
    accepts_privacy_policy: bool


@dataclass(frozen=True)
class RegisteredUser:
    id: uuid.UUID
    username: str
    email: str
    status: AccountStatus


class RegisterUser:
    def __init__(
        self,
        users: UserGateway,
        unit_of_work: UnitOfWork,
        hasher: PasswordHasher,
        password_policy: PasswordPolicy,
        mailer: VerificationMailer,
        privacy_policy_version: str,
        clock: Clock,
    ) -> None:
        self._users = users
        self._unit_of_work = unit_of_work
        self._hasher = hasher
        self._password_policy = password_policy
        self._mailer = mailer
        self._privacy_policy_version = privacy_policy_version
        self._clock = clock

    def execute(self, data: RegisterUserInput) -> RegisteredUser:
        now = self._clock()
        ensure_policy_accepted(data.accepts_privacy_policy)
        ensure_minimum_age(data.birth_date, now.date())
        self._password_policy.ensure_acceptable(data.password)

        user = User.register(
            username=data.username,
            email=data.email,
            password_hash=self._hasher.hash(data.password),
            first_name=data.first_name,
            paternal_surname=data.paternal_surname,
            maternal_surname=data.maternal_surname,
            birth_date=data.birth_date,
        )
        consent = PrivacyConsent.accept(
            user_id=user.id, policy_version=self._privacy_policy_version, now=now
        )
        self._users.add(user, consent)
        self._unit_of_work.commit()

        self._mailer.send(user, now)
        return RegisteredUser(
            id=user.id, username=user.username, email=user.email, status=user.status
        )
