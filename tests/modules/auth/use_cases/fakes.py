"""Dobles en memoria de los puertos de auth, para probar interactores sin base."""

import copy
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app.modules.auth.entities.errors import EmailTakenError, UsernameTakenError
from app.modules.auth.entities.privacy_consent import PrivacyConsent
from app.modules.auth.entities.user import User
from app.modules.auth.entities.user_session import UserSession
from app.modules.auth.use_cases.ports import (
    TokenExpiredError,
    TokenInvalidError,
    TokenPurpose,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 19, 12, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now

    def advance(self, delta: timedelta) -> None:
        self.now += delta


class FakeUnitOfWork:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


class InMemoryUserGateway:
    """Guarda copias: como una base, lo que no se guarda con save() no cambia."""

    def __init__(self) -> None:
        self.users: dict[uuid.UUID, User] = {}
        self.consents: list[PrivacyConsent] = []

    def get(self, user_id: uuid.UUID) -> User | None:
        user = self.users.get(user_id)
        return copy.deepcopy(user) if user else None

    def get_by_email(self, email: str) -> User | None:
        return self._find(lambda user: user.email.lower() == email.lower())

    def get_by_login(self, identifier: str) -> User | None:
        value = identifier.lower()
        return self._find(
            lambda user: value in (user.email.lower(), user.username.lower())
        )

    def add(self, user: User, consent: PrivacyConsent) -> None:
        if self.get_by_login(user.username):
            raise UsernameTakenError
        if self.get_by_email(user.email):
            raise EmailTakenError
        self.users[user.id] = copy.deepcopy(user)
        self.consents.append(consent)

    def save(self, user: User) -> None:
        self.users[user.id] = copy.deepcopy(user)

    def _find(self, matches: Callable[[User], bool]) -> User | None:
        found = next((user for user in self.users.values() if matches(user)), None)
        return copy.deepcopy(found) if found else None


class InMemorySessionGateway:
    def __init__(self) -> None:
        self.sessions: dict[uuid.UUID, UserSession] = {}

    def add(self, user_session: UserSession) -> None:
        self.sessions[user_session.id] = copy.deepcopy(user_session)

    def get(self, session_id: uuid.UUID) -> UserSession | None:
        found = self.sessions.get(session_id)
        return copy.deepcopy(found) if found else None

    get_for_update = get

    def save(self, user_session: UserSession) -> None:
        self.sessions[user_session.id] = copy.deepcopy(user_session)


class FakePasswordHasher:
    def __init__(self) -> None:
        self.dummy_checks = 0
        self.outdated_hashes: set[str] = set()

    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify_and_update(
        self, password: str, password_hash: str
    ) -> tuple[bool, str | None]:
        valid = password_hash in (self.hash(password), f"old:{password}")
        new_hash = (
            self.hash(password) if valid and password_hash.startswith("old:") else None
        )
        return valid, new_hash

    def verify_dummy(self, password: str) -> None:
        self.dummy_checks += 1


class FakeRefreshSecrets:
    def __init__(self) -> None:
        self._count = 0

    def new_secret(self) -> str:
        self._count += 1
        return f"secret-{self._count}"

    def hash(self, secret: str) -> str:
        return f"sha:{secret}"

    def matches(self, secret: str, stored_hash: str) -> bool:
        return self.hash(secret) == stored_hash


class FakeAccessTokens:
    """Token legible: "access|<usuario>|<sesión>|<vence>"."""

    def __init__(self, clock: FakeClock) -> None:
        self._clock = clock

    def create(
        self,
        user_id: uuid.UUID,
        session_id: uuid.UUID,
        lifetime: timedelta,
        now: datetime,
    ) -> str:
        return f"access|{user_id}|{session_id}|{(now + lifetime).isoformat()}"

    def read(self, token: str) -> tuple[uuid.UUID, uuid.UUID]:
        kind, user_id, session_id, expires = (token.split("|") + [""] * 4)[:4]
        if kind != "access":
            raise TokenInvalidError
        if datetime.fromisoformat(expires) <= self._clock():
            raise TokenExpiredError
        return uuid.UUID(user_id), uuid.UUID(session_id)


class FakeEmailLinkTokens:
    """Token legible: "<propósito>|<usuario>|<vence>"."""

    def __init__(self, clock: FakeClock) -> None:
        self._clock = clock

    def create(
        self,
        user_id: uuid.UUID,
        purpose: TokenPurpose,
        lifetime: timedelta,
        now: datetime,
    ) -> str:
        return f"{purpose.value}|{user_id}|{(now + lifetime).isoformat()}"

    def read(self, token: str, purpose: TokenPurpose) -> uuid.UUID:
        parts = token.split("|")
        if len(parts) != 3 or parts[0] != purpose.value:
            raise TokenInvalidError
        if datetime.fromisoformat(parts[2]) <= self._clock():
            raise TokenExpiredError
        try:
            return uuid.UUID(parts[1])
        except ValueError as error:
            raise TokenInvalidError from error
