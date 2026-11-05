"""Endpoints de auth: validan la entrada y llaman al servicio.

Aquí vive lo que es propio de HTTP: la cookie de web, la revisión de `Origin`
(CSRF, CLAUDE.md §9) y la cabecera `Authorization`.
"""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_session
from app.errors import AppError, ErrorResponse, ValidationErrorResponse
from app.modules.auth.models import AppUser, ClientPlatform
from app.modules.auth.repository import AuthRepository
from app.modules.auth.schemas import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    ResendVerificationRequest,
    TokenResponse,
    UserResponse,
    VerifyEmailRequest,
)
from app.modules.auth.service import (
    SESSION_LIFETIME,
    AuthConfig,
    AuthService,
    IssuedTokens,
    Login,
    NotAuthenticatedError,
    Registration,
)
from app.rate_limit import limit_by_ip

PREFIX = "/api/v1/auth"
REFRESH_COOKIE = "memories_refresh"

router = APIRouter(prefix=PREFIX, tags=["auth"])


class OriginNotAllowedError(AppError):
    status_code = 403
    code = "origin_not_allowed"
    message = "Esta petición solo se acepta desde la app web de Memories."


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

# auto_error=False: sin cabecera responde nuestro 401 con {code, message}.
_bearer = HTTPBearer(auto_error=False, description="Token de acceso (15 min)")


def get_current_user(
    service: Service,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AppUser:
    """Usuario de la petición; los demás módulos dependen de esto (design.md §5)."""
    if credentials is None:
        raise NotAuthenticatedError
    return service.authenticate(credentials.credentials)


CurrentUser = Annotated[AppUser, Depends(get_current_user)]


# ─── Registro y verificación (HU-01, HU-02) ────────────────────────────────


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


# ─── Sesión (HU-03 a HU-05) ────────────────────────────────────────────────


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
def login(body: LoginRequest, response: Response, service: Service) -> TokenResponse:
    """Inicia sesión con correo o nombre de usuario (HU-03).

    En Android el token de renovación llega en el cuerpo; en web, en una cookie
    httpOnly que el código de la app no puede leer.
    """
    issued = service.login(
        Login(
            identifier=body.identifier,
            password=body.password,
            platform=body.platform,
            device_name=body.device_name,
        )
    )
    return _token_response(issued, response)


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
    service: Service,
    body: Annotated[RefreshTokenRequest | None, Body()] = None,
) -> TokenResponse:
    """Rota el token de renovación (HU-04). Android: en el cuerpo; web: cookie."""
    refresh_token, platform = _refresh_token_from(request, body)
    issued = service.refresh(refresh_token, platform)
    return _token_response(issued, response)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {"model": ErrorResponse, "description": "Origen no permitido (web)"}
    },
)
def logout(
    request: Request,
    service: Service,
    body: Annotated[RefreshTokenRequest | None, Body()] = None,
) -> Response:
    """Revoca la sesión de este dispositivo (HU-05). Repetirlo no da error."""
    refresh_token, platform = _refresh_token_from(request, body)
    service.logout(refresh_token, platform)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    if platform is ClientPlatform.WEB:
        response.delete_cookie(
            REFRESH_COOKIE, path=PREFIX, secure=True, httponly=True, samesite="strict"
        )
    return response


def _refresh_token_from(
    request: Request, body: RefreshTokenRequest | None
) -> tuple[str | None, ClientPlatform]:
    """Saca el token del cuerpo (Android) o de la cookie (web)."""
    if body is not None:
        return body.refresh_token, ClientPlatform.ANDROID
    # La cookie la manda el navegador solo: hay que comprobar que la petición
    # viene de la app web y no de otro sitio (CSRF).
    if request.headers.get("origin") != request.app.state.settings.web_app_origin:
        raise OriginNotAllowedError
    return request.cookies.get(REFRESH_COOKIE), ClientPlatform.WEB


def _token_response(issued: IssuedTokens, response: Response) -> TokenResponse:
    if issued.platform is ClientPlatform.ANDROID:
        return TokenResponse(
            access_token=issued.access_token,
            expires_in=issued.expires_in,
            refresh_token=issued.refresh_token,
        )
    response.set_cookie(
        REFRESH_COOKIE,
        issued.refresh_token,
        max_age=int(SESSION_LIFETIME.total_seconds()),
        path=PREFIX,
        secure=True,
        httponly=True,
        samesite="strict",
    )
    return TokenResponse(access_token=issued.access_token, expires_in=issued.expires_in)
