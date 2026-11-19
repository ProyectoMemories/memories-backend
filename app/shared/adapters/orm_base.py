"""Base de los modelos ORM. Las tablas las crea la migración 0001, no SQLAlchemy."""

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    # Todo timestamp es timestamptz (CLAUDE.md §8).
    type_annotation_map = {datetime: DateTime(timezone=True)}
