"""Base declarativa de SQLAlchemy.

Todas las tablas viven en el esquema de Postgres definido en `DB_SCHEMA`
(`memories` por defecto), no en `public`.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

from app.config.settings import get_settings

settings = get_settings()

# Nombres deterministas para indices y restricciones: sin esto, Alembic
# genera nombres distintos en cada maquina y las migraciones divergen.
NAMING_CONVENTION = {
    # Sin %(column_0_label)s a proposito: con un esquema propio incluiria el
    # nombre del esquema y saldrian nombres como ix_memories_memories_owner_id.
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(schema=settings.DB_SCHEMA, naming_convention=NAMING_CONVENTION)
