from app.rate_limit import RateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_el_sexto_intento_se_rechaza_y_pasa_al_minuto() -> None:
    clock = FakeClock()
    limiter = RateLimiter(limit=5, window_seconds=60, clock=clock)

    assert all(limiter.hit("ip") is None for _ in range(5))
    clock.now = 59
    assert limiter.hit("ip") == 1  # espera el segundo que falta

    clock.now = 60
    assert limiter.hit("ip") is None


def test_cada_clave_cuenta_por_separado() -> None:
    limiter = RateLimiter(limit=1, window_seconds=60, clock=FakeClock())

    assert limiter.hit("a") is None
    assert limiter.hit("b") is None
    assert limiter.hit("a") is not None
