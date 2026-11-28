"""Caso de uso: ver mi perfil (HU-01, RF-04).

Recibe el id de quien hace la petición, que sale de su token; nunca uno que
venga de la URL o del cuerpo, así nadie puede pedir el perfil de otra cuenta
(RNF-02).
"""

import uuid

from app.modules.users.entities.profile import Profile
from app.modules.users.use_cases.errors import ProfileNotFoundError
from app.modules.users.use_cases.ports import ProfileGateway


class GetMyProfile:
    def __init__(self, profiles: ProfileGateway) -> None:
        self._profiles = profiles

    def execute(self, user_id: uuid.UUID) -> Profile:
        profile = self._profiles.get(user_id)
        if profile is None:
            raise ProfileNotFoundError
        return profile
