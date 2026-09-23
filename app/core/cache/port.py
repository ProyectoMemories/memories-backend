"""Contrato de cache.

Lo implementan Redis (ejecucion normal) y un diccionario en memoria (tests).
Sobre esta interfaz se apoyan el almacen de refresh tokens y el rate limiting,
asi que los tests no necesitan Redis levantado.
"""

from typing import Protocol


class CachePort(Protocol):
    async def get(self, key: str) -> str | None: ...

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None: ...

    async def delete(self, key: str) -> None: ...

    async def increment(self, key: str, ttl_seconds: int) -> int:
        """Suma 1 y devuelve el valor. Fija el TTL la primera vez."""
        ...

    async def ping(self) -> bool: ...

    async def close(self) -> None: ...
