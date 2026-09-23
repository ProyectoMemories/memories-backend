"""Composicion de dependencias del modulo de recuerdos.

Un solo archivo con todo el cableado: los routers solo reciben casos de uso ya
construidos.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_session
from app.config.settings import Settings, get_settings
from app.core.storage.factory import get_storage
from app.core.storage.port import StoragePort
from app.modules.memories.application.image_validator import PhotoUploadRules
from app.modules.memories.application.photo_url_service import PhotoUrlService
from app.modules.memories.application.use_cases.attach_photos import AttachPhotos
from app.modules.memories.application.use_cases.create_memory import CreateMemory
from app.modules.memories.application.use_cases.delete_memory import DeleteMemory
from app.modules.memories.application.use_cases.delete_photo import DeletePhoto
from app.modules.memories.application.use_cases.get_memory import GetMemory
from app.modules.memories.application.use_cases.get_memory_calendar import GetMemoryCalendar
from app.modules.memories.application.use_cases.get_photo_content import GetPhotoContent
from app.modules.memories.application.use_cases.list_memories import ListMemories
from app.modules.memories.application.use_cases.remove_photo import RemovePhoto
from app.modules.memories.application.use_cases.revive_memories import ReviveMemories
from app.modules.memories.application.use_cases.update_memory import UpdateMemory
from app.modules.memories.application.use_cases.upload_photo import UploadPhoto
from app.modules.memories.domain.repositories.memory_repository import MemoryRepository
from app.modules.memories.domain.repositories.photo_repository import PhotoRepository
from app.modules.memories.infrastructure.repositories.sqlalchemy_memory_repository import (
    SQLAlchemyMemoryRepository,
)
from app.modules.memories.infrastructure.repositories.sqlalchemy_photo_repository import (
    SQLAlchemyPhotoRepository,
)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
StorageDep = Annotated[StoragePort, Depends(get_storage)]


def get_memory_repository(session: SessionDep) -> MemoryRepository:
    return SQLAlchemyMemoryRepository(session)


def get_photo_repository(session: SessionDep) -> PhotoRepository:
    return SQLAlchemyPhotoRepository(session)


MemoryRepositoryDep = Annotated[MemoryRepository, Depends(get_memory_repository)]
PhotoRepositoryDep = Annotated[PhotoRepository, Depends(get_photo_repository)]


def get_photo_upload_rules(settings: SettingsDep) -> PhotoUploadRules:
    return PhotoUploadRules(
        allowed_content_types=frozenset(settings.allowed_image_content_types),
        max_size_bytes=settings.max_photo_size_bytes,
    )


def get_photo_url_service(storage: StorageDep, settings: SettingsDep) -> PhotoUrlService:
    return PhotoUrlService(
        storage=storage,
        raw_url_template=f"{settings.API_PREFIX}/photos/{{photo_id}}/raw",
    )


PhotoUrlServiceDep = Annotated[PhotoUrlService, Depends(get_photo_url_service)]


# ─── Casos de uso ────────────────────────────────────────────────────


def create_memory_use_case(
    memories: MemoryRepositoryDep, photos: PhotoRepositoryDep, settings: SettingsDep
) -> CreateMemory:
    return CreateMemory(memories, photos, settings.MAX_PHOTOS_PER_MEMORY)


def list_memories_use_case(memories: MemoryRepositoryDep) -> ListMemories:
    return ListMemories(memories)


def get_memory_use_case(memories: MemoryRepositoryDep) -> GetMemory:
    return GetMemory(memories)


def update_memory_use_case(memories: MemoryRepositoryDep) -> UpdateMemory:
    return UpdateMemory(memories)


def delete_memory_use_case(memories: MemoryRepositoryDep, storage: StorageDep) -> DeleteMemory:
    return DeleteMemory(memories, storage)


def attach_photos_use_case(
    memories: MemoryRepositoryDep, photos: PhotoRepositoryDep, settings: SettingsDep
) -> AttachPhotos:
    return AttachPhotos(memories, photos, settings.MAX_PHOTOS_PER_MEMORY)


def remove_photo_use_case(
    memories: MemoryRepositoryDep, photos: PhotoRepositoryDep, storage: StorageDep
) -> RemovePhoto:
    return RemovePhoto(memories, photos, storage)


def get_memory_calendar_use_case(memories: MemoryRepositoryDep) -> GetMemoryCalendar:
    return GetMemoryCalendar(memories)


def revive_memories_use_case(memories: MemoryRepositoryDep) -> ReviveMemories:
    return ReviveMemories(memories)


def upload_photo_use_case(
    photos: PhotoRepositoryDep,
    storage: StorageDep,
    rules: Annotated[PhotoUploadRules, Depends(get_photo_upload_rules)],
) -> UploadPhoto:
    return UploadPhoto(photos, storage, rules)


def get_photo_content_use_case(photos: PhotoRepositoryDep, storage: StorageDep) -> GetPhotoContent:
    return GetPhotoContent(photos, storage)


def delete_photo_use_case(photos: PhotoRepositoryDep, storage: StorageDep) -> DeletePhoto:
    return DeletePhoto(photos, storage)
