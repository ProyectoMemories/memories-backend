"""Endpoints de usuarios."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.security.dependencies import CurrentUserDep, SuperuserDep
from app.modules.users.application.use_cases.get_user_profile import GetUserProfile
from app.modules.users.application.use_cases.list_users import ListUsers
from app.modules.users.application.use_cases.update_user_profile import UpdateUserProfile
from app.modules.users.interfaces.http.dependencies import (
    get_user_profile_use_case,
    list_users_use_case,
    update_user_profile_use_case,
)
from app.modules.users.interfaces.http.schemas.user_schemas import (
    UpdateProfileRequest,
    UserListResponse,
    UserResponse,
)
from app.shared.pagination import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, PageRequest

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("/me", response_model=UserResponse, summary="Perfil del usuario autenticado")
async def get_me(
    current_user: CurrentUserDep,
    use_case: Annotated[GetUserProfile, Depends(get_user_profile_use_case)],
) -> UserResponse:
    return UserResponse.from_entity(await use_case.execute(current_user.id))


@router.patch("/me", response_model=UserResponse, summary="Actualizar el propio perfil")
async def update_me(
    payload: UpdateProfileRequest,
    current_user: CurrentUserDep,
    use_case: Annotated[UpdateUserProfile, Depends(update_user_profile_use_case)],
) -> UserResponse:
    user = await use_case.execute(current_user.id, payload.display_name)
    return UserResponse.from_entity(user)


@router.get(
    "",
    response_model=UserListResponse,
    summary="Listar usuarios (solo superusuario)",
)
async def list_users(
    _: SuperuserDep,
    use_case: Annotated[ListUsers, Depends(list_users_use_case)],
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
) -> UserListResponse:
    return UserListResponse.from_page(await use_case.execute(PageRequest(page=page, size=size)))
