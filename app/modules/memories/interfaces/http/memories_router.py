"""Endpoints de recuerdos.

Las rutas fijas (/calendar, /revive) se declaran antes que /{memory_id} para
que no las capture el parametro.
"""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.security.dependencies import CurrentUserDep
from app.modules.memories.application.use_cases.attach_photos import (
    AttachPhotos,
    AttachPhotosCommand,
)
from app.modules.memories.application.use_cases.create_memory import (
    CreateMemory,
    CreateMemoryCommand,
)
from app.modules.memories.application.use_cases.delete_memory import DeleteMemory
from app.modules.memories.application.use_cases.get_memory import GetMemory
from app.modules.memories.application.use_cases.get_memory_calendar import GetMemoryCalendar
from app.modules.memories.application.use_cases.list_memories import (
    ListMemories,
    ListMemoriesQuery,
)
from app.modules.memories.application.use_cases.remove_photo import RemovePhoto
from app.modules.memories.application.use_cases.revive_memories import ReviveMemories
from app.modules.memories.application.use_cases.update_memory import (
    UpdateMemory,
    UpdateMemoryCommand,
)
from app.modules.memories.interfaces.http.dependencies import (
    PhotoUrlServiceDep,
    attach_photos_use_case,
    create_memory_use_case,
    delete_memory_use_case,
    get_memory_calendar_use_case,
    get_memory_use_case,
    list_memories_use_case,
    remove_photo_use_case,
    revive_memories_use_case,
    update_memory_use_case,
)
from app.modules.memories.interfaces.http.presenters import to_memory_response
from app.modules.memories.interfaces.http.schemas.memory_schemas import (
    CalendarDayResponse,
    CalendarResponse,
    CreateMemoryRequest,
    MemoryListResponse,
    MemoryResponse,
    ReviveResponse,
    UpdateMemoryRequest,
)
from app.modules.memories.interfaces.http.schemas.photo_schemas import AttachPhotosRequest
from app.shared.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, PageRequest

router = APIRouter(prefix="/memories", tags=["Recuerdos"])


@router.post(
    "",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un recuerdo",
)
async def create_memory(
    payload: CreateMemoryRequest,
    current_user: CurrentUserDep,
    use_case: Annotated[CreateMemory, Depends(create_memory_use_case)],
    urls: PhotoUrlServiceDep,
) -> MemoryResponse:
    memory = await use_case.execute(
        CreateMemoryCommand(
            owner_id=current_user.id,
            title=payload.title,
            moment_date=payload.moment_date,
            description=payload.description,
            photo_ids=payload.photo_ids,
        )
    )
    return await to_memory_response(memory, urls)


@router.get("", response_model=MemoryListResponse, summary="Listar mis recuerdos")
async def list_memories(
    current_user: CurrentUserDep,
    use_case: Annotated[ListMemories, Depends(list_memories_use_case)],
    urls: PhotoUrlServiceDep,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    date_from: date | None = None,
    date_to: date | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
) -> MemoryListResponse:
    result = await use_case.execute(
        ListMemoriesQuery(
            owner_id=current_user.id,
            page=PageRequest(page=page, size=size),
            date_from=date_from,
            date_to=date_to,
            search=q,
        )
    )
    return MemoryListResponse(
        items=[await to_memory_response(memory, urls) for memory in result.items],
        total=result.total,
        page=result.page,
        size=result.size,
        pages=result.pages,
    )


@router.get("/calendar", response_model=CalendarResponse, summary="Recuerdos por dia del mes")
async def get_calendar(
    current_user: CurrentUserDep,
    use_case: Annotated[GetMemoryCalendar, Depends(get_memory_calendar_use_case)],
    year: Annotated[int, Query(ge=1900, le=2999)],
    month: Annotated[int, Query(ge=1, le=12)],
) -> CalendarResponse:
    days = await use_case.execute(current_user.id, year, month)
    return CalendarResponse(
        year=year,
        month=month,
        days=[CalendarDayResponse.from_entity(day) for day in days],
    )


@router.get("/revive", response_model=ReviveResponse, summary="Volver a descubrir recuerdos")
async def revive(
    current_user: CurrentUserDep,
    use_case: Annotated[ReviveMemories, Depends(revive_memories_use_case)],
    urls: PhotoUrlServiceDep,
) -> ReviveResponse:
    selection = await use_case.execute(current_user.id)
    return ReviveResponse(
        reason=selection.reason.value,
        memories=[await to_memory_response(memory, urls) for memory in selection.memories],
    )


@router.get("/{memory_id}", response_model=MemoryResponse, summary="Detalle de un recuerdo")
async def get_memory(
    memory_id: uuid.UUID,
    current_user: CurrentUserDep,
    use_case: Annotated[GetMemory, Depends(get_memory_use_case)],
    urls: PhotoUrlServiceDep,
) -> MemoryResponse:
    memory = await use_case.execute(memory_id, current_user.id)
    return await to_memory_response(memory, urls)


@router.patch("/{memory_id}", response_model=MemoryResponse, summary="Editar un recuerdo")
async def update_memory(
    memory_id: uuid.UUID,
    payload: UpdateMemoryRequest,
    current_user: CurrentUserDep,
    use_case: Annotated[UpdateMemory, Depends(update_memory_use_case)],
    urls: PhotoUrlServiceDep,
) -> MemoryResponse:
    memory = await use_case.execute(
        UpdateMemoryCommand(
            memory_id=memory_id,
            owner_id=current_user.id,
            title=payload.title,
            moment_date=payload.moment_date,
            description=payload.description,
            clear_description=payload.clear_description,
        )
    )
    return await to_memory_response(memory, urls)


@router.delete(
    "/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Borrar un recuerdo",
)
async def delete_memory(
    memory_id: uuid.UUID,
    current_user: CurrentUserDep,
    use_case: Annotated[DeleteMemory, Depends(delete_memory_use_case)],
) -> Response:
    await use_case.execute(memory_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{memory_id}/photos",
    response_model=MemoryResponse,
    summary="Anadir fotografias a un recuerdo",
)
async def attach_photos(
    memory_id: uuid.UUID,
    payload: AttachPhotosRequest,
    current_user: CurrentUserDep,
    use_case: Annotated[AttachPhotos, Depends(attach_photos_use_case)],
    urls: PhotoUrlServiceDep,
) -> MemoryResponse:
    memory = await use_case.execute(
        AttachPhotosCommand(
            memory_id=memory_id,
            owner_id=current_user.id,
            photo_ids=payload.photo_ids,
        )
    )
    return await to_memory_response(memory, urls)


@router.delete(
    "/{memory_id}/photos/{photo_id}",
    response_model=MemoryResponse,
    summary="Quitar una fotografia de un recuerdo",
)
async def remove_photo(
    memory_id: uuid.UUID,
    photo_id: uuid.UUID,
    current_user: CurrentUserDep,
    use_case: Annotated[RemovePhoto, Depends(remove_photo_use_case)],
    urls: PhotoUrlServiceDep,
) -> MemoryResponse:
    memory = await use_case.execute(memory_id, photo_id, current_user.id)
    return await to_memory_response(memory, urls)
