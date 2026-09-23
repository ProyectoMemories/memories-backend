"""Endpoints de fotografias.

Viven en el modulo de recuerdos porque la fotografia no tiene sentido por si
sola: es parte del recuerdo. Cuelgan de /photos porque se suben antes de que el
recuerdo exista.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Response, UploadFile, status

from app.core.security.dependencies import CurrentUserDep
from app.modules.memories.application.use_cases.delete_photo import DeletePhoto
from app.modules.memories.application.use_cases.get_photo_content import GetPhotoContent
from app.modules.memories.application.use_cases.upload_photo import (
    UploadPhoto,
    UploadPhotoCommand,
)
from app.modules.memories.interfaces.http.dependencies import (
    PhotoUrlServiceDep,
    delete_photo_use_case,
    get_photo_content_use_case,
    upload_photo_use_case,
)
from app.modules.memories.interfaces.http.schemas.photo_schemas import PhotoResponse

router = APIRouter(prefix="/photos", tags=["Fotografias"])


@router.post(
    "",
    response_model=PhotoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subir una fotografia",
)
async def upload_photo(
    current_user: CurrentUserDep,
    use_case: Annotated[UploadPhoto, Depends(upload_photo_use_case)],
    urls: PhotoUrlServiceDep,
    file: Annotated[UploadFile, File(description="Imagen JPEG, PNG o WebP")],
) -> PhotoResponse:
    data = await file.read()
    photo = await use_case.execute(
        UploadPhotoCommand(
            owner_id=current_user.id,
            content_type=file.content_type or "",
            data=data,
        )
    )
    return PhotoResponse.from_entity(photo, await urls.url_for(photo))


@router.get(
    "/{photo_id}/raw",
    summary="Descargar la imagen por la API",
    response_class=Response,
)
async def get_photo_raw(
    photo_id: uuid.UUID,
    current_user: CurrentUserDep,
    use_case: Annotated[GetPhotoContent, Depends(get_photo_content_use_case)],
) -> Response:
    content = await use_case.execute(photo_id, current_user.id)
    return Response(
        content=content.data,
        media_type=content.content_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.delete(
    "/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Descartar una fotografia sin recuerdo",
)
async def delete_photo(
    photo_id: uuid.UUID,
    current_user: CurrentUserDep,
    use_case: Annotated[DeletePhoto, Depends(delete_photo_use_case)],
) -> Response:
    await use_case.execute(photo_id, current_user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
