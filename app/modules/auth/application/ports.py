"""Puertos que necesita la autenticacion.

El almacen de refresh tokens se declara aqui (quien lo necesita) y se
implementa en infrastructure/. Asi el caso de uso no sabe si detras hay Redis,
un diccionario o cualquier otra cosa.
"""

import uuid
from typing import Protocol


class RefreshTokenStore(Protocol):
    async def remember(self, user_id: uuid.UUID, jti: str, ttl_seconds: int) -> None:
        """Registra un refresh token como valido."""
        ...

    async def is_valid(self, user_id: uuid.UUID, jti: str) -> bool: ...

    async def revoke(self, user_id: uuid.UUID, jti: str) -> None: ...

    async def revoke_all(self, user_id: uuid.UUID) -> None:
        """Cierra todas las sesiones del usuario."""
        ...
