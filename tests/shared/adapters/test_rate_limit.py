from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.shared.adapters.error_presenter import register_error_handlers
from app.shared.adapters.rate_limit import InMemoryRateLimiter, limit_by_ip


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_el_sexto_intento_se_rechaza_y_pasa_al_minuto() -> None:
    clock = FakeClock()
    limiter = InMemoryRateLimiter(limit=5, window_seconds=60, clock=clock)

    assert all(limiter.hit("ip") is None for _ in range(5))
    clock.now = 59
    assert limiter.hit("ip") == 1  # espera el segundo que falta

    clock.now = 60
    assert limiter.hit("ip") is None


def test_cada_clave_cuenta_por_separado() -> None:
    limiter = InMemoryRateLimiter(limit=1, window_seconds=60, clock=FakeClock())

    assert limiter.hit("a") is None
    assert limiter.hit("b") is None
    assert limiter.hit("a") is not None


def test_una_x_forwarded_for_inventada_no_esquiva_el_limite() -> None:
    """La IP sale de la conexión, no de una cabecera que manda el cliente."""
    app = FastAPI()
    app.state.rate_limiter = InMemoryRateLimiter(limit=1, window_seconds=60)
    register_error_handlers(app)

    @app.post("/intento", dependencies=[Depends(limit_by_ip("intento"))])
    def attempt() -> None:
        return None

    client = TestClient(app)
    first = client.post("/intento", headers={"X-Forwarded-For": "10.0.0.1"})
    second = client.post("/intento", headers={"X-Forwarded-For": "10.0.0.2"})

    assert first.status_code == 200
    assert second.status_code == 429
