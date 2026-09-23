"""Crea el superusuario inicial.

Uso:
    docker compose exec api python scripts/seed.py

Lee SEED_SUPERUSER_EMAIL / SEED_SUPERUSER_PASSWORD del entorno si estan
definidas. No pisa nada: si la cuenta ya existe, no hace nada.
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config.database import session_factory  # noqa: E402
from app.core.security.hashing.factory import get_password_hashing_service  # noqa: E402
from app.modules.users.domain.entities.user import User  # noqa: E402
from app.modules.users.domain.value_objects.email import Email  # noqa: E402
from app.modules.users.infrastructure.repositories.sqlalchemy_user_repository import (  # noqa: E402
    SQLAlchemyUserRepository,
)
from app.shared.roles import UserRole  # noqa: E402

EMAIL = os.getenv("SEED_SUPERUSER_EMAIL", "admin@memories.local")
PASSWORD = os.getenv("SEED_SUPERUSER_PASSWORD", "memories2026")
DISPLAY_NAME = os.getenv("SEED_SUPERUSER_NAME", "Superusuario")


async def main() -> None:
    hashing = get_password_hashing_service()
    async with session_factory() as session:
        users = SQLAlchemyUserRepository(session)
        email = Email(EMAIL)

        if await users.exists_with_email(email):
            print(f"El superusuario {email} ya existe. No se hace nada.")
            return

        user = User.register(
            email=email,
            display_name=DISPLAY_NAME,
            password_hash=hashing.hash(PASSWORD),
            role=UserRole.SUPERUSER,
        )
        await users.add(user)
        await session.commit()
        print(f"Superusuario creado: {email}")


if __name__ == "__main__":
    asyncio.run(main())
