"""Endpoints de autenticacion.

Todos llevan rate limiting: sin el, probar contrasenas a ciegas sale gratis.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.config.settings import get_settings
from app.core.rate_limit import rate_limit
from app.core.security.dependencies import CurrentUserDep
from app.modules.auth.application.use_cases.authenticate_user import AuthenticateUser
from app.modules.auth.application.use_cases.logout_user import LogoutUser
from app.modules.auth.application.use_cases.refresh_session import RefreshSession
from app.modules.auth.application.use_cases.register_user import RegisterUser, RegisterUserCommand
from app.modules.auth.interfaces.http.dependencies import (
    authenticate_user_use_case,
    logout_user_use_case,
    refresh_session_use_case,
    register_user_use_case,
)
from app.modules.auth.interfaces.http.schemas import (
    LoginRequest,
    LogoutRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    SessionResponse,
)
from app.modules.users.interfaces.http.schemas.user_schemas import UserResponse

settings = get_settings()

router = APIRouter(
    prefix="/auth",
    tags=["Autenticacion"],
    dependencies=[Depends(rate_limit("auth", settings.RATE_LIMIT_AUTH_PER_MINUTE))],
)


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una cuenta",
)
async def register(
    payload: RegisterRequest,
    use_case: Annotated[RegisterUser, Depends(register_user_use_case)],
) -> UserResponse:
    user = await use_case.execute(
        RegisterUserCommand(
            email=str(payload.email),
            display_name=payload.display_name,
            password=payload.password,
        )
    )
    return UserResponse.from_entity(user)


@router.post("/login", response_model=SessionResponse, summary="Iniciar sesion")
async def login(
    payload: LoginRequest,
    use_case: Annotated[AuthenticateUser, Depends(authenticate_user_use_case)],
) -> SessionResponse:
    session = await use_case.execute(str(payload.email), payload.password)
    return SessionResponse.from_session(session)


@router.post("/refresh", response_model=SessionResponse, summary="Renovar la sesion")
async def refresh(
    payload: RefreshRequest,
    use_case: Annotated[RefreshSession, Depends(refresh_session_use_case)],
) -> SessionResponse:
    session = await use_case.execute(payload.refresh_token)
    return SessionResponse.from_session(session)


@router.post("/logout", response_model=MessageResponse, summary="Cerrar sesion")
async def logout(
    payload: LogoutRequest,
    current_user: CurrentUserDep,
    use_case: Annotated[LogoutUser, Depends(logout_user_use_case)],
) -> MessageResponse:
    await use_case.execute(
        current_user.id,
        payload.refresh_token,
        all_devices=payload.all_devices,
    )
    return MessageResponse(message="Sesion cerrada.")
