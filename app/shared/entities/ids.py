"""Ids de las entidades: UUIDv7 generados en el backend, no en la base (D41, D54)."""

import uuid

from uuid6 import uuid7


def new_id() -> uuid.UUID:
    """UUIDv7: ordenado por tiempo y difícil de adivinar."""
    return uuid.UUID(bytes=uuid7().bytes)
