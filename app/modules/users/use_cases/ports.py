"""Puertos de users: lo que los interactores necesitan del exterior."""

import uuid
from typing import Protocol

from app.modules.users.entities.profile import Profile


class ProfileGateway(Protocol):
    def get(self, user_id: uuid.UUID) -> Profile | None: ...
