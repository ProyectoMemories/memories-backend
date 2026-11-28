"""Router de users, bajo /api/v1/users."""

from fastapi import APIRouter

from app.modules.auth.adapters.controllers.dependencies import CurrentUser
from app.modules.users.adapters.controllers.dependencies import UseCases
from app.modules.users.adapters.presenters.profile_presenter import present_profile
from app.modules.users.adapters.presenters.responses import ProfileResponse
from app.shared.adapters.error_presenter import ErrorResponse

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get(
    "/me",
    responses={
        401: {
            "model": ErrorResponse,
            "description": "Sin token, token vencido o sesión cerrada",
        }
    },
)
def get_my_profile(user: CurrentUser, use_cases: UseCases) -> ProfileResponse:
    """Datos de quien inició sesión (HU-01). El id sale del token (RNF-02)."""
    profile = use_cases.get_my_profile().execute(user.id)
    return present_profile(profile)
