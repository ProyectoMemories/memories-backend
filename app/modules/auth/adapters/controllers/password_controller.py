"""Controller de contraseñas: recuperar y cambiar (HU-06, HU-07)."""

from fastapi import APIRouter, Depends, Response, status

from app.modules.auth.adapters.controllers.dependencies import CurrentUser, UseCases
from app.modules.auth.adapters.controllers.requests import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from app.modules.auth.use_cases.change_password import ChangePasswordInput
from app.modules.auth.use_cases.reset_password import ResetPasswordInput
from app.shared.adapters.error_presenter import ErrorResponse
from app.shared.adapters.rate_limit import limit_by_ip

router = APIRouter(prefix="/password")


@router.post(
    "/forgot",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(limit_by_ip("password_forgot"))],
    responses={429: {"model": ErrorResponse, "description": "Demasiados intentos"}},
)
def forgot_password(body: ForgotPasswordRequest, use_cases: UseCases) -> Response:
    """Envía el enlace de recuperación. Responde igual exista o no la cuenta."""
    use_cases.request_password_reset().execute(body.email)
    return Response(status_code=status.HTTP_202_ACCEPTED)


@router.post(
    "/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {
            "model": ErrorResponse,
            "description": "Enlace vencido, inválido o usado",
        },
        422: {"model": ErrorResponse, "description": "Contraseña que no cumple D62-B"},
    },
)
def reset_password(body: ResetPasswordRequest, use_cases: UseCases) -> Response:
    """Guarda la contraseña nueva y cierra todas las sesiones (HU-06)."""
    use_cases.reset_password().execute(
        ResetPasswordInput(token=body.token, new_password=body.new_password)
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/change",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(limit_by_ip("password_change"))],
    responses={
        401: {"model": ErrorResponse, "description": "Sin sesión"},
        422: {
            "model": ErrorResponse,
            "description": "Actual incorrecta o nueva inválida",
        },
        429: {"model": ErrorResponse, "description": "Demasiados intentos"},
    },
)
def change_password(
    body: ChangePasswordRequest, user: CurrentUser, use_cases: UseCases
) -> Response:
    """Cambia la contraseña y cierra todas las sesiones, también esta (HU-07)."""
    use_cases.change_password().execute(
        ChangePasswordInput(
            user_id=user.id,
            current_password=body.current_password,
            new_password=body.new_password,
        )
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
