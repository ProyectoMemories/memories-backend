"""Caso de uso: renovar la sesion con el refresh token.

Rotacion: cada renovacion invalida el token usado y entrega uno nuevo. Si
alguien roba un refresh token y lo usa, el legitimo deja de funcionar y el robo
se nota.
"""

from app.core.security.tokens.jwt_service import JWTService
from app.modules.auth.application.ports import RefreshTokenStore
from app.modules.auth.application.session import AuthenticatedSession
from app.modules.users.domain.repositories.user_repository import UserRepository
from app.shared.errors import AuthenticationError


class RefreshSession:
    def __init__(
        self,
        users: UserRepository,
        jwt_service: JWTService,
        refresh_tokens: RefreshTokenStore,
    ) -> None:
        self._users = users
        self._jwt = jwt_service
        self._refresh_tokens = refresh_tokens

    async def execute(self, refresh_token: str) -> AuthenticatedSession:
        claims = self._jwt.decode(refresh_token, expected_type="refresh")

        if not await self._refresh_tokens.is_valid(claims.subject, claims.jti):
            raise AuthenticationError("La sesion ya no es valida. Inicia sesion de nuevo.")
        await self._refresh_tokens.revoke(claims.subject, claims.jti)

        user = await self._users.get_by_id(claims.subject)
        if user is None or not user.is_active:
            raise AuthenticationError("La sesion ya no es valida. Inicia sesion de nuevo.")

        access = self._jwt.create_access_token(user.id, user.role.value)
        refresh = self._jwt.create_refresh_token(user.id, user.role.value)
        await self._refresh_tokens.remember(
            user.id, refresh.jti, self._jwt.refresh_token_ttl_seconds
        )

        return AuthenticatedSession(
            user=user,
            access_token=access.token,
            refresh_token=refresh.token,
            access_token_expires_in=self._jwt.access_token_ttl_seconds,
        )
