"""Traduccion entre la entidad Photo y la fila de photos."""

from app.modules.memories.domain.entities.photo import Photo
from app.modules.memories.infrastructure.models.photo_model import PhotoModel


def to_entity(model: PhotoModel) -> Photo:
    return Photo(
        id=model.id,
        owner_id=model.owner_id,
        storage_key=model.storage_key,
        content_type=model.content_type,
        size_bytes=model.size_bytes,
        checksum_sha256=model.checksum_sha256,
        memory_id=model.memory_id,
        position=model.position,
        created_at=model.created_at,
    )


def to_model(entity: Photo) -> PhotoModel:
    return PhotoModel(
        id=entity.id,
        owner_id=entity.owner_id,
        memory_id=entity.memory_id,
        storage_key=entity.storage_key,
        content_type=entity.content_type,
        size_bytes=entity.size_bytes,
        checksum_sha256=entity.checksum_sha256,
        position=entity.position,
    )


def apply_changes(entity: Photo, model: PhotoModel) -> None:
    model.memory_id = entity.memory_id
    model.position = entity.position
