"""Límite de intentos por IP, en memoria del proceso (D62-F).

Cada proceso cuenta por separado y el conteo se pierde al reiniciar: alcanza
para el MVP con un solo proceso (specs/auth/design.md §6).
"""

import math
import time
from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock

from fastapi import Request

from app.errors import TooManyRequestsError


class RateLimiter:
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
        ip = request.client.host if request.client else "unknown"
        wait = request.app.state.rate_limiter.hit(f"{action}:{ip}")
        if wait is not None:
            raise TooManyRequestsError(headers={"Retry-After": str(math.ceil(wait))})

    return dependency
