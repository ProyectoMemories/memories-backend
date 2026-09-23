"""Traduccion entre la entidad Memory y la fila de memories."""

from app.modules.memories.domain.entities.memory import Memory
from app.modules.memories.infrastructure.mappers import photo_mapper
from app.modules.memories.infrastructure.models.memory_model import MemoryModel


def to_entity(model: MemoryModel) -> Memory:
    return Memory(
        id=model.id,
        owner_id=model.owner_id,
        title=model.title,
        moment_date=model.moment_date,
        description=model.description,
        photos=[photo_mapper.to_entity(photo) for photo in model.photos],
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def to_model(entity: Memory) -> MemoryModel:
    return MemoryModel(
        id=entity.id,
        owner_id=entity.owner_id,
        title=entity.title,
        moment_date=entity.moment_date,
        description=entity.description,
    )


def apply_changes(entity: Memory, model: MemoryModel) -> None:
    model.title = entity.title
    model.moment_date = entity.moment_date
    model.description = entity.description
