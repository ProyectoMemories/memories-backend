"""Caso de uso: iniciar sesion.

Aqui ocurre el re-hasheo transparente: si la contrasena guardada usa un
algoritmo o unos parametros distintos a los configurados ahora, se vuelve a
hashear con los nuevos sin que el usuario note nada (RNF-08).
"""

from app.core.security.hashing.service import PasswordHashingService
from app.core.security.tokens.jwt_service import JWTService
from app.modules.auth.application.ports import RefreshTokenStore
from app.modules.auth.application.session import AuthenticatedSession
from app.modules.users.domain.errors import InvalidEmailError
from app.modules.users.domain.repositories.user_repository import UserRepository
from app.modules.users.domain.value_objects.email import Email
from app.shared.errors import AuthenticationError

# Mismo mensaje para correo inexistente y contrasena incorrecta: decir cual de
# las dos falla es contarle a quien prueba credenciales que ese correo existe.
CREDENCIALES_INVALIDAS = "Correo o contrasena incorrectos."


class AuthenticateUser:
    def __init__(
        self,
        users: UserRepository,
        hashing: PasswordHashingService,
        jwt_service: JWTService,
        refresh_tokens: RefreshTokenStore,
    ) -> None:
        self._users = users
        self._hashing = hashing
        self._jwt = jwt_service
        self._refresh_tokens = refresh_tokens

    async def execute(self, email: str, password: str) -> AuthenticatedSession:
        try:
            parsed_email = Email(email)
        except InvalidEmailError as exc:
            raise AuthenticationError(CREDENCIALES_INVALIDAS) from exc

        user = await self._users.get_by_email(parsed_email)
        if user is None or not self._hashing.verify(password, user.password_hash):
            raise AuthenticationError(CREDENCIALES_INVALIDAS)
        if not user.is_active:
            raise AuthenticationError("La cuenta esta desactivada.")

        if self._hashing.needs_rehash(user.password_hash):
            user.change_password_hash(self._hashing.hash(password))
            await self._users.update(user)

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
