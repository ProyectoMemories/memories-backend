"""Elige la implementacion de cache segun CACHE_PROVIDER."""

from functools import lru_cache

from app.config.settings import Settings, get_settings
from app.core.cache.memory_cache import MemoryCache
from app.core.cache.port import CachePort
from app.core.cache.redis_cache import RedisCache


def build_cache(settings: Settings) -> CachePort:
    if settings.CACHE_PROVIDER == "redis":
        return RedisCache(settings.REDIS_URL)
    return MemoryCache()


@lru_cache(maxsize=1)
def get_cache() -> CachePort:
    return build_cache(get_settings())
