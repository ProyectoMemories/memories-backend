"""Límite de intentos en Redis, compartido por todos los procesos (D77).

Ventana fija: el primer intento crea la clave con un vencimiento de 60 s y los
siguientes la incrementan. `INCR`, `EXPIRE NX` y `TTL` van en una sola
transacción, así una clave nunca queda sin vencimiento (eso bloquearía la IP
para siempre). Requiere Redis 7 o superior (`EXPIRE NX`).

Si Redis no responde, se cuenta en memoria: nunca se quita el límite. Tras un
fallo se deja de intentar con Redis durante una pausa, para que una caída no
demore cada petición ni llene el log con un aviso por intento.
"""

import logging
import time
from collections.abc import Callable

import redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from app.shared.adapters.rate_limit import RateLimit

# Por si la instancia de Redis se comparte con otro proyecto.
KEY_PREFIX = "memories:ratelimit:"

# Con Redis caído, cada petición espera como mucho esto antes de pasar a memoria.
TIMEOUT_SECONDS = 0.5

# Tras un fallo, cuánto tiempo se cuenta solo en memoria antes de volver a probar.
PAUSE_AFTER_FAILURE_SECONDS = 30

logger = logging.getLogger(__name__)


def connect_redis(url: str) -> redis.Redis:
    """Cliente sin reintentos y con timeouts cortos: fallar rápido, no esperar."""
    return redis.Redis.from_url(
        url,
        socket_timeout=TIMEOUT_SECONDS,
        socket_connect_timeout=TIMEOUT_SECONDS,
        retry=Retry(NoBackoff(), retries=0),
    )


class RedisRateLimiter:
    def __init__(
        self,
        client: redis.Redis,
        fallback: RateLimit,
        limit: int = 5,
        window_seconds: int = 60,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._client = client
        self._fallback = fallback
        self._limit = limit
        self._window = window_seconds
        self._clock = clock
        self._redis_paused_until = 0.0

    def hit(self, key: str) -> float | None:
        if self._clock() < self._redis_paused_until:
            return self._fallback.hit(key)
        try:
            return self._hit_in_redis(f"{KEY_PREFIX}{key}")
        except redis.RedisError as error:
            self._redis_paused_until = self._clock() + PAUSE_AFTER_FAILURE_SECONDS
            # Solo el error: la URL con la contraseña no está en el mensaje.
            logger.warning(
                "Redis no responde; durante %s s el límite de intentos se cuenta "
                "en memoria: %s",
                PAUSE_AFTER_FAILURE_SECONDS,
                error,
            )
            return self._fallback.hit(key)

    def _hit_in_redis(self, name: str) -> float | None:
        with self._client.pipeline(transaction=True) as transaction:
            transaction.incr(name)
            transaction.expire(name, self._window, nx=True)
            transaction.ttl(name)
            attempts, _, seconds_left = transaction.execute()
        if attempts <= self._limit:
            return None
        return float(max(seconds_left, 1))
