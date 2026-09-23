"""Almacen de refresh tokens sobre el cache (Redis en ejecucion normal).

Se guarda un unico registro por usuario con los jti vigentes y su vencimiento:
    auth:refresh:{user_id} -> {"<jti>": <epoch>, ...}

Asi cerrar todas las sesiones es borrar una clave, sin recorrer Redis con SCAN.

Consecuencia asumida: si Redis se vacia, todo el mundo tiene que volver a
iniciar sesion. Para este MVP es aceptable; si deja de serlo, esta clase se
sustituye por una tabla sin tocar los casos de uso.
"""

import json
import time
import uuid

from app.core.cache.port import CachePort

KEY_PREFIX = "auth:refresh"


class CacheRefreshTokenStore:
    def __init__(self, cache: CachePort) -> None:
        self._cache = cache

    @staticmethod
    def _key(user_id: uuid.UUID) -> str:
        return f"{KEY_PREFIX}:{user_id}"

    async def _load(self, user_id: uuid.UUID) -> dict[str, int]:
        raw = await self._cache.get(self._key(user_id))
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        now = int(time.time())
        return {jti: int(exp) for jti, exp in data.items() if int(exp) > now}

    async def _save(self, user_id: uuid.UUID, tokens: dict[str, int]) -> None:
        if not tokens:
            await self._cache.delete(self._key(user_id))
            return
        ttl = max(tokens.values()) - int(time.time())
        await self._cache.set(self._key(user_id), json.dumps(tokens), max(ttl, 1))

    async def remember(self, user_id: uuid.UUID, jti: str, ttl_seconds: int) -> None:
        tokens = await self._load(user_id)
        tokens[jti] = int(time.time()) + ttl_seconds
        await self._save(user_id, tokens)

    async def is_valid(self, user_id: uuid.UUID, jti: str) -> bool:
        return jti in await self._load(user_id)

    async def revoke(self, user_id: uuid.UUID, jti: str) -> None:
        tokens = await self._load(user_id)
        tokens.pop(jti, None)
        await self._save(user_id, tokens)

    async def revoke_all(self, user_id: uuid.UUID) -> None:
        await self._cache.delete(self._key(user_id))
