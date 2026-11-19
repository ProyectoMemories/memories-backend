"""UserGateway con SQLAlchemy: app_user y privacy_consent."""

import uuid

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.auth.adapters.gateways import mappers
from app.modules.auth.adapters.gateways.orm_models import UserRecord
from app.modules.auth.entities.errors import EmailTakenError, UsernameTakenError
from app.modules.auth.entities.privacy_consent import PrivacyConsent
from app.modules.auth.entities.user import User
from app.shared.entities.errors import ConflictError

_UNIQUE_VIOLATION = "23505"
_CONFLICT_BY_CONSTRAINT: dict[str, type[ConflictError]] = {
    "uq_app_user_username_ci": UsernameTakenError,
    "uq_app_user_email_ci": EmailTakenError,
}


class SqlUserGateway:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: uuid.UUID) -> User | None:
        record = self._session.get(UserRecord, user_id)
        return mappers.user_to_entity(record) if record else None

    def get_for_update(self, user_id: uuid.UUID) -> User | None:
        record = self._session.get(UserRecord, user_id, with_for_update=True)
        return mappers.user_to_entity(record) if record else None

    def get_by_email(self, email: str) -> User | None:
        # lower() usa el índice uq_app_user_email_ci (RN-09).
        return self._one(func.lower(UserRecord.email) == email.lower())

    def get_by_login(self, identifier: str) -> User | None:
        value = identifier.lower()
        # Un correo lleva "@" y un nombre de usuario no: hay a lo sumo uno.
        return self._one(
            or_(
                func.lower(UserRecord.email) == value,
                func.lower(UserRecord.username) == value,
            )
        )

    def add(self, user: User, consent: PrivacyConsent) -> None:
        try:
            self._session.add(mappers.new_user_record(user))
            # Sin este flush, el ORM podría insertar el consentimiento primero.
            self._session.flush()
            self._session.add(mappers.new_consent_record(consent))
            self._session.flush()
        except IntegrityError as error:
            self._session.rollback()
            conflict = _conflict_for(error)
            if conflict is None:
                raise
            raise conflict from error

    def save(self, user: User) -> None:
        record = self._session.get(UserRecord, user.id)
        if record is None:
            raise LookupError(f"No existe el usuario {user.id}")
        mappers.copy_user_changes(user, record)

    def _one(self, condition: ColumnElement[bool]) -> User | None:
        record = self._session.scalars(
            select(UserRecord).where(condition)
        ).one_or_none()
        return mappers.user_to_entity(record) if record else None


def _conflict_for(error: IntegrityError) -> ConflictError | None:
    """El error de negocio de la restricción única violada, si es una conocida."""
    if getattr(error.orig, "sqlstate", None) != _UNIQUE_VIOLATION:
        return None
    constraint = error.orig.diag.constraint_name  # type: ignore[union-attr]
    conflict = _CONFLICT_BY_CONSTRAINT.get(constraint or "")
    return conflict() if conflict else None
