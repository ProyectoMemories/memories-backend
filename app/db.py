"""Acceso a PostgreSQL con SQLAlchemy (síncrono) y generación de ids UUIDv7."""

import uuid
from collections.abc import Iterator
from datetime import datetime

from fastapi import Request
from sqlalchemy import DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from uuid6 import uuid7


class Base(DeclarativeBase):
    """Base de los modelos. Las tablas las crea la migración 0001, no SQLAlchemy."""

    # Todo timestamp es timestamptz (CLAUDE.md §8).
    type_annotation_map = {datetime: DateTime(timezone=True)}


class UniqueViolationError(Exception):
    """Otro registro ya usa ese valor. Lleva el nombre de la restricción."""

    def __init__(self, constraint: str | None) -> None:
        super().__init__(constraint)
        self.constraint = constraint


def new_id() -> uuid.UUID:
    """UUIDv7: ordenado por tiempo y difícil de adivinar (D41, D54)."""
    return uuid.UUID(bytes=uuid7().bytes)


def create_sessionmaker(database_url: str) -> sessionmaker[Session]:
    # create_engine no se conecta todavía: la API arranca aunque la base no esté.
    engine = create_engine(database_url, pool_pre_ping=True)
    return sessionmaker(engine, expire_on_commit=False)


def get_session(request: Request) -> Iterator[Session]:
    """Una sesión por petición. Lo que no se confirmó con commit se descarta."""
    with request.app.state.sessionmaker() as session:
        yield session
