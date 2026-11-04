"""Único punto de acceso a app_user y privacy_consent (CLAUDE.md §7)."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import UniqueViolationError
from app.modules.auth.models import AppUser, PrivacyConsent

_UNIQUE_VIOLATION = "23505"


class AuthRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_user(self, user_id: uuid.UUID) -> AppUser | None:
        return self._session.get(AppUser, user_id)

    def get_user_by_email(self, email: str) -> AppUser | None:
        # lower() usa el índice uq_app_user_email_ci (RN-09).
        query = select(AppUser).where(func.lower(AppUser.email) == email.lower())
        return self._session.scalars(query).one_or_none()

    def add_user(self, user: AppUser, consent: PrivacyConsent) -> None:
        with self._unique_violations():
            self._session.add(user)
            # Sin este flush, el ORM podría insertar el consentimiento primero.
            self._session.flush()
            self._session.add(consent)
            self._session.flush()

    def commit(self) -> None:
        self._session.commit()

    @contextmanager
    def _unique_violations(self) -> Iterator[None]:
        """Convierte un valor repetido en UniqueViolationError con su restricción."""
        try:
            yield
        except IntegrityError as error:
            self._session.rollback()
            if getattr(error.orig, "sqlstate", None) != _UNIQUE_VIOLATION:
                raise
            raise UniqueViolationError(error.orig.diag.constraint_name) from error
