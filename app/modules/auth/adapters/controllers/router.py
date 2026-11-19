"""Router de auth: reúne los controllers bajo /api/v1/auth."""

from fastapi import APIRouter

from app.modules.auth.adapters.controllers import (
    registration_controller,
    session_controller,
)
from app.modules.auth.adapters.presenters.refresh_cookie import AUTH_PREFIX

router = APIRouter(prefix=AUTH_PREFIX, tags=["auth"])
router.include_router(registration_controller.router)
router.include_router(session_controller.router)
