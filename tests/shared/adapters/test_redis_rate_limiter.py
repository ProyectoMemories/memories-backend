"""Límite de intentos compartido en Redis (D77), contra Redis real."""

import uuid

import pytest
import redis

from app.shared.adapters.rate_limit import InMemoryRateLimiter
from app.shared.adapters.redis_rate_limiter import (
    KEY_PREFIX,
    RedisRateLimiter,
    connect_redis,
)


def _new_key() -> str:
    """Una clave por prueba: no choca con otras corridas ni con datos reales."""
    return f"prueba:{uuid.uuid4()}"


def _limiter(client: redis.Redis, limit: int = 5) -> RedisRateLimiter:
    return RedisRateLimiter(client, InMemoryRateLimiter(limit=limit), limit=limit)


def test_el_sexto_intento_se_rechaza_con_la_espera_que_queda(
    redis_client: redis.Redis,
) -> None:
    limiter = _limiter(redis_client)
    key = _new_key()

    assert all(limiter.hit(key) is None for _ in range(5))
    wait = limiter.hit(key)

    assert wait is not None
    assert 1 <= wait <= 60


def test_cada_clave_cuenta_por_separado(redis_client: redis.Redis) -> None:
    limiter = _limiter(redis_client, limit=1)
    first, second = _new_key(), _new_key()

    assert limiter.hit(first) is None
    assert limiter.hit(second) is None
    assert limiter.hit(first) is not None


def test_la_clave_siempre_vence(redis_client: redis.Redis) -> None:
    limiter = _limiter(redis_client)
    key = _new_key()

    limiter.hit(key)
    limiter.hit(key)

    assert 0 < redis_client.ttl(f"{KEY_PREFIX}{key}") <= 60


def test_dos_procesos_comparten_el_conteo(redis_client: redis.Redis) -> None:
    """Dos instancias (como dos procesos de la API) suman en el mismo contador."""
    first_process, second_process = _limiter(redis_client), _limiter(redis_client)
    key = _new_key()

    for _ in range(3):
        first_process.hit(key)
    for _ in range(2):
        second_process.hit(key)

    assert first_process.hit(key) is not None


def test_si_redis_no_responde_cuenta_en_memoria(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Puerto 1: nadie escucha; la conexión falla enseguida.
    limiter = _limiter(connect_redis("redis://127.0.0.1:1/0"), limit=1)

    assert limiter.hit("ip") is None
    assert limiter.hit("ip") is not None
    assert "Redis no responde" in caplog.text
