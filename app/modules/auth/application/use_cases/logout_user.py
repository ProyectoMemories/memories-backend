"""Caso de uso: cerrar sesion.

El token de acceso es sin estado y sigue siendo valido hasta que vence (30
minutos como maximo); lo que se revoca aqui es el de refresco, que es el que
permite seguir dentro.
"""

import uuid

from app.core.security.tokens.jwt_service import JWTService
from app.modules.auth.application.ports import RefreshTokenStore
from app.shared.errors import AuthenticationError


class LogoutUser:
    def __init__(self, jwt_service: JWTService, refresh_tokens: RefreshTokenStore) -> None:
        self._jwt = jwt_service
        self._refresh_tokens = refresh_tokens

    async def execute(
        self,
        user_id: uuid.UUID,
        refresh_token: str | None = None,
        *,
        all_devices: bool = False,
    ) -> None:
        if all_devices or refresh_token is None:
            await self._refresh_tokens.revoke_all(user_id)
            return

        try:
            claims = self._jwt.decode(refresh_token, expected_type="refresh")
        except AuthenticationError:
            # Cerrar sesion es idempotente: si el token ya no vale, no hay nada
            # que revocar y se responde igual.
            return

        if claims.subject != user_id:
            # El token es de otra cuenta: se cierran las sesiones de quien pide,
            # nunca las de un tercero.
            await self._refresh_tokens.revoke_all(user_id)
            return

        await self._refresh_tokens.revoke(user_id, claims.jti)
