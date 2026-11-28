"""Composición de users: conecta cada puerto con su adaptador.

users todavía no tiene nada que crear una sola vez (hash, tokens): solo arma,
para cada petición, los interactores con gateways sobre su sesión de base.
"""

from sqlalchemy.orm import Session

from app.modules.users.adapters.gateways.profile_gateway import SqlProfileGateway
from app.modules.users.use_cases.get_my_profile import GetMyProfile


class UsersUseCaseFactory:
    """Interactores de una petición. Implementa UsersUseCases (adapters/controllers)."""

    def __init__(self, session: Session) -> None:
        self._profiles = SqlProfileGateway(session)

    def get_my_profile(self) -> GetMyProfile:
        return GetMyProfile(self._profiles)


class UsersModule:
    def use_cases(self, session: Session) -> UsersUseCaseFactory:
        return UsersUseCaseFactory(session)
