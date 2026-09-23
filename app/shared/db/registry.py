"""Punto unico donde se importan todos los modelos.

Alembic y los tests necesitan que `Base.metadata` conozca todas las tablas.
Como cada tabla vive en su propio archivo, alguien tiene que importarlas: es
este modulo. Al crear una tabla nueva, anadela aqui.
"""

from app.modules.memories.infrastructure.models.memory_model import MemoryModel
from app.modules.memories.infrastructure.models.photo_model import PhotoModel
from app.modules.users.infrastructure.models.user_model import UserModel
from app.shared.db.base import Base

__all__ = ["Base", "MemoryModel", "PhotoModel", "UserModel"]
