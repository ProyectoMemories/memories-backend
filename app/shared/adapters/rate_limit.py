"""Límite de intentos por IP (D62-F, D70, D77).

`RateLimit` es el contrato que usa `limit_by_ip`. Lo cumplen el contador en
memoria de este archivo y el de Redis (`redis_rate_limiter.py`), que comparten
todos los procesos. `create_app` elige cuál usar.
"""

import math
import time
from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock
from typing import Protocol

from fastapi import Request

from app.shared.entities.errors import TooManyRequestsError


class RateLimit(Protocol):
    def hit(self, key: str) -> float | None:
        """Registra un intento. Devuelve los segundos a esperar si se pasó."""
        ...


class InMemoryRateLimiter:
    """Ventana deslizante en la memoria del proceso.

    Cada proceso cuenta por separado y el conteo se pierde al reiniciar. Se usa
    sin Redis (pruebas, API sin Docker) y cuando Redis no responde.
    """

    def __init__(
        self,
        limit: int = 5,
        window_seconds: float = 60,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        # Los endpoints síncronos corren en varios hilos a la vez.
        self._lock = Lock()

    def hit(self, key: str) -> float | None:
        """Registra un intento. Devuelve los segundos a esperar si se pasó."""
        now = self._clock()
        with self._lock:
            hits = self._hits[key]
            while hits and now - hits[0] >= self._window:
                hits.popleft()
            if len(hits) >= self._limit:
                return self._window - (now - hits[0])
            hits.append(now)
            return None


def limit_by_ip(action: str) -> Callable[[Request], None]:
    """Dependencia de FastAPI que aplica el límite a un endpoint."""

    def dependency(request: Request) -> None:
        # Nunca X-Forwarded-For: el cliente la escribe a su gusto. Detrás de un
        # proxy, uvicorn la aplica solo si viene de uno de confianza (D77).
        ip = request.client.host if request.client else "unknown"
        rate_limiter: RateLimit = request.app.state.rate_limiter
        wait = rate_limiter.hit(f"{action}:{ip}")
        if wait is not None:
            raise TooManyRequestsError(retry_after_seconds=math.ceil(wait))

    return dependency
