"""Limite de peticiones por minuto, apoyado en el cache.

Su razon de ser es el inicio de sesion: sin esto, probar contrasenas a ciegas
sale gratis. La ventana es fija de 60 segundos y la clave es la IP de origen.
"""

from collections.abc import Awaitable, Callable

from fastapi import Depends, Request

from app.core.cache.factory import get_cache
from app.core.cache.port import CachePort
from app.shared.errors import RateLimitExceededError

WINDOW_SECONDS = 60


def rate_limit(bucket: str, per_minute: int) -> Callable[..., Awaitable[None]]:
    """Crea una dependencia de FastAPI que limita un grupo de endpoints."""

    async def dependency(
        request: Request,
        cache: CachePort = Depends(get_cache),
    ) -> None:
        client_ip = request.client.host if request.client else "desconocido"
        key = f"ratelimit:{bucket}:{client_ip}"
        try:
            attempts = await cache.increment(key, WINDOW_SECONDS)
        except Exception:  # noqa: BLE001 - si el cache cae, no se bloquea el servicio
            return
        if attempts > per_minute:
            raise RateLimitExceededError(
                "Demasiados intentos. Espera un minuto antes de volver a intentarlo."
            )

    return dependency
