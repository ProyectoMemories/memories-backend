"""Controller de registro y verificación del correo (HU-01, HU-02)."""

from fastapi import APIRouter, Depends, Response, status

from app.modules.auth.adapters.controllers.dependencies import UseCases
from app.modules.auth.adapters.controllers.requests import (
    RegisterRequest,
    ResendVerificationRequest,
    VerifyEmailRequest,
)
from app.modules.auth.adapters.presenters.responses import UserResponse
from app.modules.auth.adapters.presenters.user_presenter import present_registered_user
from app.modules.auth.use_cases.register_user import RegisterUserInput
from app.shared.adapters.error_presenter import ErrorResponse, ValidationErrorResponse
from app.shared.adapters.rate_limit import limit_by_ip

router = APIRouter()


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(limit_by_ip("register"))],
    responses={
        409: {"model": ErrorResponse, "description": "Usuario o correo en uso"},
        422: {"model": ValidationErrorResponse, "description": "Datos inválidos"},
        429: {"model": ErrorResponse, "description": "Demasiados intentos"},
    },
)
def register(body: RegisterRequest, use_cases: UseCases) -> UserResponse:
    """Crea la cuenta sin verificar y envía el correo de verificación (HU-01)."""
    registered = use_cases.register_user().execute(
        RegisterUserInput(**body.model_dump())
    )
    return present_registered_user(registered)


@router.post(
    "/verify-email",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {"model": ErrorResponse, "description": "Enlace vencido o inválido"}
    },
)
def verify_email(body: VerifyEmailRequest, use_cases: UseCases) -> Response:
    """Activa la cuenta con el token del enlace del correo (HU-02)."""
    use_cases.verify_email().execute(body.token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/verify-email/resend",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(limit_by_ip("verify_email_resend"))],
    responses={429: {"model": ErrorResponse, "description": "Demasiados intentos"}},
)
def resend_verification(
    body: ResendVerificationRequest, use_cases: UseCases
) -> Response:
    """Reenvía el enlace. Responde igual exista o no la cuenta (HU-02)."""
    use_cases.resend_verification().execute(body.email)
    return Response(status_code=status.HTTP_202_ACCEPTED)
