"""ProfileGateway con SQLAlchemy: lee el perfil en app_user."""

import uuid

from sqlalchemy.orm import Session

from app.modules.users.adapters.gateways.orm_models import ProfileRecord
from app.modules.users.entities.profile import Profile


class SqlProfileGateway:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: uuid.UUID) -> Profile | None:
        record = self._session.get(ProfileRecord, user_id)
        if record is None:
            return None
        return Profile(
            id=record.id,
            username=record.username,
            email=record.email,
            first_name=record.first_name,
            paternal_surname=record.paternal_surname,
            maternal_surname=record.maternal_surname,
        )
