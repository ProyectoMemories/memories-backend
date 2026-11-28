"""Inyección de dependencias de los controllers de users.

Igual que en auth: `main.open_request_scope` deja en `request.state.users` la
fábrica de interactores de la petición, y este círculo no importa
`frameworks/` (CLAUDE.md §7).
"""

from typing import Annotated, Protocol

from fastapi import Depends, Request

from app.modules.users.use_cases.get_my_profile import GetMyProfile


class UsersUseCases(Protocol):
    """Lo que los controllers necesitan; lo implementa frameworks/composition.py."""

    def get_my_profile(self) -> GetMyProfile: ...


def get_users_use_cases(request: Request) -> UsersUseCases:
    use_cases: UsersUseCases = request.state.users  # lo deja main.open_request_scope
    return use_cases


UseCases = Annotated[UsersUseCases, Depends(get_users_use_cases)]
