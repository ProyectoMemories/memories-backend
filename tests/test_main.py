"""Raíz de composición: qué adaptadores elige create_app."""

from app.main import create_app
from app.shared.adapters.rate_limit import InMemoryRateLimiter
from app.shared.adapters.redis_rate_limiter import RedisRateLimiter
from tests.conftest import FakeEmailSender, make_settings


def test_con_redis_url_cuenta_en_redis() -> None:
    settings = make_settings().model_copy(
        update={"redis_url": "redis://127.0.0.1:6379/0"}
    )

    app = create_app(settings, email_sender=FakeEmailSender())

    assert isinstance(app.state.rate_limiter, RedisRateLimiter)


def test_sin_redis_url_cuenta_en_memoria() -> None:
    app = create_app(make_settings(), email_sender=FakeEmailSender())

    assert isinstance(app.state.rate_limiter, InMemoryRateLimiter)
