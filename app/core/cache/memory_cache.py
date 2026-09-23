"""Cache en memoria del proceso.

Para tests y para arrancar sin Redis. No sirve con varios workers: cada uno
tendria su propia copia.
"""

import time
from dataclasses import dataclass


@dataclass(slots=True)
class _Entry:
    value: str
    expires_at: float | None

    def expired(self, now: float) -> bool:
        return self.expires_at is not None and now >= self.expires_at


class MemoryCache:
    def __init__(self) -> None:
        self._data: dict[str, _Entry] = {}

    async def get(self, key: str) -> str | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        if entry.expired(time.monotonic()):
            self._data.pop(key, None)
            return None
        return entry.value

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        expires_at = time.monotonic() + ttl_seconds if ttl_seconds else None
        self._data[key] = _Entry(value=value, expires_at=expires_at)

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)

    async def increment(self, key: str, ttl_seconds: int) -> int:
        current = await self.get(key)
        value = int(current) + 1 if current is not None else 1
        entry = self._data.get(key)
        expires_at = entry.expires_at if entry and not entry.expired(time.monotonic()) else None
        if expires_at is None:
            expires_at = time.monotonic() + ttl_seconds
        self._data[key] = _Entry(value=str(value), expires_at=expires_at)
        return value

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        self._data.clear()
