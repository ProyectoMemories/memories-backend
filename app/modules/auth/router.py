"""Endpoints de auth: validan la entrada y llaman al servicio."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.errors import ErrorResponse, ValidationErrorResponse
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    RegisterRequest,
    ResendVerificationRequest,
    UserResponse,
    VerifyEmailRequest,
)
from app.modules.auth.service import AuthConfig, AuthService, Registration
from app.rate_limit import limit_by_ip

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def get_auth_service(
    request: Request, session: Annotated[Session, Depends(get_session)]
) -> AuthService:
    state = request.app.state
    return AuthService(
        repository=AuthRepository(session),
        hasher=state.password_hasher,
        email_sender=state.email_sender,
        config=AuthConfig(
            secret_key=state.settings.secret_key,
            privacy_policy_version=state.settings.privacy_policy_version,
            web_app_origin=state.settings.web_app_origin,
        ),
    )


Service = Annotated[AuthService, Depends(get_auth_service)]


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse, "description": "Usuario o correo en uso"},
        422: {"model": ValidationErrorResponse, "description": "Datos inválidos"},
    },
)
def register(body: RegisterRequest, service: Service) -> UserResponse:
    """Crea la cuenta sin verificar y envía el correo de verificación (HU-01)."""
    user = service.register(Registration(**body.model_dump()))
    return UserResponse.model_validate(user, from_attributes=True)


@router.post(
    "/verify-email",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {"model": ErrorResponse, "description": "Enlace vencido o inválido"}
    },
)
def verify_email(body: VerifyEmailRequest, service: Service) -> Response:
    """Activa la cuenta con el token del enlace del correo (HU-02)."""
    service.verify_email(body.token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/verify-email/resend",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(limit_by_ip("verify_email_resend"))],
    responses={429: {"model": ErrorResponse, "description": "Demasiados intentos"}},
)
def resend_verification(body: ResendVerificationRequest, service: Service) -> Response:
    """Reenvía el enlace. Responde igual exista o no la cuenta (HU-02)."""
    service.resend_verification(body.email)
    return Response(status_code=status.HTTP_202_ACCEPTED)
