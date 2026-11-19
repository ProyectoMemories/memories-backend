"""UnitOfWork sobre una sesión de SQLAlchemy (una por petición)."""

from sqlalchemy.orm import Session


class SqlUnitOfWork:
    def __init__(self, session: Session) -> None:
        self._session = session

    def commit(self) -> None:
        self._session.commit()
