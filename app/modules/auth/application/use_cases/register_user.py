"""Caso de uso: registrar una cuenta.

El modulo auth no tiene dominio propio: orquesta el dominio de usuarios con los
servicios de seguridad. Por eso aqui no hay carpeta domain/ (no se crean
carpetas vacias "por simetria").

Depende del *puerto* UserRepository, nunca de la infraestructura de usuarios.
"""

from dataclasses import dataclass

from app.core.security.hashing.service import PasswordHashingService
from app.modules.users.domain.entities.user import User
from app.modules.users.domain.errors import EmailAlreadyRegisteredError
from app.modules.users.domain.repositories.user_repository import UserRepository
from app.modules.users.domain.value_objects.email import Email
from app.modules.users.domain.value_objects.password import RawPassword
from app.shared.roles import UserRole


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    email: str
    display_name: str
    password: str
    role: UserRole = UserRole.USER


class RegisterUser:
    def __init__(self, users: UserRepository, hashing: PasswordHashingService) -> None:
        self._users = users
        self._hashing = hashing

    async def execute(self, command: RegisterUserCommand) -> User:
        email = Email(command.email)
        password = RawPassword(command.password)

        if await self._users.exists_with_email(email):
            raise EmailAlreadyRegisteredError()

        user = User.register(
            email=email,
            display_name=command.display_name,
            password_hash=self._hashing.hash(password.value),
            role=command.role,
        )
        await self._users.add(user)
        return user
