"""Controller de sesión: login, refresh y logout (HU-03 a HU-05).

En Android el token de renovación viaja en el cuerpo; en web, en una cookie
httpOnly que el código de la app no puede leer (D56).
"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, Response, status

from app.modules.auth.adapters.controllers.dependencies import UseCases
from app.modules.auth.adapters.controllers.refresh_token_source import (
    refresh_token_from,
)
from app.modules.auth.adapters.controllers.requests import (
    LoginRequest,
    RefreshTokenRequest,
)
from app.modules.auth.adapters.presenters.refresh_cookie import delete_refresh_cookie
from app.modules.auth.adapters.presenters.responses import TokenResponse
from app.modules.auth.adapters.presenters.token_presenter import present_tokens
from app.modules.auth.entities.user_session import ClientPlatform
from app.modules.auth.use_cases.log_in import LogInInput
from app.modules.auth.use_cases.log_out import LogOutInput
from app.modules.auth.use_cases.refresh_session import RefreshSessionInput
from app.shared.adapters.error_presenter import ErrorResponse
from app.shared.adapters.rate_limit import limit_by_ip

router = APIRouter()

OptionalRefreshBody = Annotated[RefreshTokenRequest | None, Body()]


@router.post(
    "/login",
    response_model_exclude_none=True,
    dependencies=[Depends(limit_by_ip("login"))],
    responses={
        401: {"model": ErrorResponse, "description": "Credenciales incorrectas"},
        403: {
            "model": ErrorResponse,
            "description": "Correo sin verificar o cuenta suspendida",
        },
        429: {"model": ErrorResponse, "description": "Demasiados intentos"},
    },
)
def login(body: LoginRequest, response: Response, use_cases: UseCases) -> TokenResponse:
    """Inicia sesión con correo o nombre de usuario (HU-03)."""
    issued = use_cases.log_in().execute(LogInInput(**body.model_dump()))
    return present_tokens(issued, response)


@router.post(
    "/refresh",
    response_model_exclude_none=True,
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Sesión vencida, revocada o token reusado",
        },
        403: {"model": ErrorResponse, "description": "Origen no permitido (web)"},
    },
)
def refresh(
    request: Request,
    response: Response,
    use_cases: UseCases,
    body: OptionalRefreshBody = None,
) -> TokenResponse:
    """Rota el token de renovación (HU-04). Android: en el cuerpo; web: cookie."""
    refresh_token, platform = refresh_token_from(request, body)
    issued = use_cases.refresh_session().execute(
        RefreshSessionInput(refresh_token=refresh_token, platform=platform)
    )
    return present_tokens(issued, response)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"model": ErrorResponse, "description": "Origen no permitido (web)"}
    },
)
def logout(
    request: Request, use_cases: UseCases, body: OptionalRefreshBody = None
) -> Response:
    """Revoca la sesión de este dispositivo (HU-05). Repetirlo no da error."""
    refresh_token, platform = refresh_token_from(request, body)
    use_cases.log_out().execute(
        LogOutInput(refresh_token=refresh_token, platform=platform)
    )
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    if platform is ClientPlatform.WEB:
        delete_refresh_cookie(response)
    return response
