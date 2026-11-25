"""Límite de intentos compartido en Redis (D77), contra Redis real."""

import socket
import time
import uuid

import pytest
import redis

from app.shared.adapters.rate_limit import InMemoryRateLimiter
from app.shared.adapters.redis_rate_limiter import (
    KEY_PREFIX,
    PAUSE_AFTER_FAILURE_SECONDS,
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


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _unreachable(clock: FakeClock, limit: int = 5) -> RedisRateLimiter:
    # Puerto 1: nadie escucha; la conexión se rechaza enseguida.
    client = connect_redis("redis://:clave-secreta@127.0.0.1:1/0")
    return RedisRateLimiter(
        client, InMemoryRateLimiter(limit=limit), limit=limit, clock=clock
    )


def test_si_redis_no_responde_cuenta_en_memoria_sin_mostrar_la_clave(
    caplog: pytest.LogCaptureFixture,
) -> None:
    limiter = _unreachable(FakeClock(), limit=1)

    assert limiter.hit("ip") is None
    assert limiter.hit("ip") is not None
    assert "Redis no responde" in caplog.text
    assert "clave-secreta" not in caplog.text


def test_tras_un_fallo_no_insiste_con_redis_hasta_que_pasa_la_pausa(
    caplog: pytest.LogCaptureFixture,
) -> None:
    clock = FakeClock()
    limiter = _unreachable(clock)

    for _ in range(3):
        limiter.hit("ip")
    assert caplog.text.count("Redis no responde") == 1

    clock.now = PAUSE_AFTER_FAILURE_SECONDS
    limiter.hit("ip")
    assert caplog.text.count("Redis no responde") == 2


def test_un_redis_colgado_no_demora_mas_que_el_timeout() -> None:
    """Acepta la conexión y nunca responde: cada intento espera como mucho 0,5 s."""
    with socket.socket() as hung_server:
        hung_server.bind(("127.0.0.1", 0))
        hung_server.listen()
        port = hung_server.getsockname()[1]
        client = connect_redis(f"redis://127.0.0.1:{port}/0")
        limiter = RedisRateLimiter(client, InMemoryRateLimiter())

        started = time.monotonic()
        first = limiter.hit("ip")
        second = limiter.hit("ip")
        elapsed = time.monotonic() - started

    assert first is None and second is None
    # Uno espera el timeout; el siguiente ya no prueba Redis (pausa).
    assert elapsed < 1.0
