"""Presenta el perfil de quien hace la petición."""

from app.modules.users.adapters.presenters.responses import ProfileResponse
from app.modules.users.entities.profile import Profile


def present_profile(profile: Profile) -> ProfileResponse:
    return ProfileResponse(
        id=profile.id,
        username=profile.username,
        email=profile.email,
        first_name=profile.first_name,
        paternal_surname=profile.paternal_surname,
        maternal_surname=profile.maternal_surname,
    )
