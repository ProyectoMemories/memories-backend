"""Montaje de los routers de la version 1 de la API.

Anadir un modulo es anadir una linea aqui.
"""

from fastapi import APIRouter

from app.modules.auth.interfaces.http.router import router as auth_router
from app.modules.memories.interfaces.http.memories_router import router as memories_router
from app.modules.memories.interfaces.http.photos_router import router as photos_router
from app.modules.users.interfaces.http.router import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(photos_router)
api_router.include_router(memories_router)
