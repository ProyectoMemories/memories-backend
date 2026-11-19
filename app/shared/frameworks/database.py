"""Motor de PostgreSQL con SQLAlchemy síncrono (D65)."""

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_sessionmaker(database_url: str) -> sessionmaker[Session]:
    # create_engine no se conecta todavía: la API arranca aunque la base no esté.
    engine = create_engine(database_url, pool_pre_ping=True)
    return sessionmaker(engine, expire_on_commit=False)
