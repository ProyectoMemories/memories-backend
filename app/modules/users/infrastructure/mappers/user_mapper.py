"""Traduccion entre la entidad de dominio y la fila de la tabla.

Es el precio de que el dominio no dependa del ORM, y es el sitio donde se paga:
un unico archivo por modulo, en vez de reglas de negocio mezcladas con columnas.
"""

from app.modules.users.domain.entities.user import User
from app.modules.users.domain.value_objects.email import Email
from app.modules.users.infrastructure.models.user_model import UserModel


def to_entity(model: UserModel) -> User:
    return User(
        id=model.id,
        email=Email(model.email),
        display_name=model.display_name,
        password_hash=model.password_hash,
        role=model.role,
        is_active=model.is_active,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def to_model(entity: User) -> UserModel:
    return UserModel(
        id=entity.id,
        email=entity.email.value,
        display_name=entity.display_name,
        password_hash=entity.password_hash,
        role=entity.role,
        is_active=entity.is_active,
    )


def apply_changes(entity: User, model: UserModel) -> None:
    model.email = entity.email.value
    model.display_name = entity.display_name
    model.password_hash = entity.password_hash
    model.role = entity.role
    model.is_active = entity.is_active
