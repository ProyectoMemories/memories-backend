"""SessionGateway con SQLAlchemy: user_session."""

import uuid
from datetime import datetime

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.modules.auth.adapters.gateways import mappers
from app.modules.auth.adapters.gateways.orm_models import UserSessionRecord
from app.modules.auth.entities.user_session import UserSession


class SqlSessionGateway:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, user_session: UserSession) -> None:
        self._session.add(mappers.new_session_record(user_session))

    def get(self, session_id: uuid.UUID) -> UserSession | None:
        record = self._session.get(UserSessionRecord, session_id)
        return mappers.session_to_entity(record) if record else None

    def get_for_update(self, session_id: uuid.UUID) -> UserSession | None:
        record = self._session.get(UserSessionRecord, session_id, with_for_update=True)
        return mappers.session_to_entity(record) if record else None

    def save(self, user_session: UserSession) -> None:
        record = self._session.get(UserSessionRecord, user_session.id)
        if record is None:
            raise LookupError(f"No existe la sesión {user_session.id}")
        mappers.copy_session_changes(user_session, record)

    def revoke_all(self, user_id: uuid.UUID, now: datetime) -> None:
        # Un solo UPDATE: no hace falta traer las sesiones para cerrarlas.
        self._session.execute(
            update(UserSessionRecord)
            .where(
                UserSessionRecord.user_id == user_id,
                UserSessionRecord.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
