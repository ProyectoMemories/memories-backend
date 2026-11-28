"""GetMyProfile con un doble del gateway, sin base de datos (HU-01)."""

import uuid

import pytest

from app.modules.users.entities.profile import Profile
from app.modules.users.use_cases.errors import ProfileNotFoundError
from app.modules.users.use_cases.get_my_profile import GetMyProfile


class InMemoryProfileGateway:
    def __init__(self, *profiles: Profile) -> None:
        self._profiles = {profile.id: profile for profile in profiles}

    def get(self, user_id: uuid.UUID) -> Profile | None:
        return self._profiles.get(user_id)


def _profile(username: str) -> Profile:
    return Profile(
        id=uuid.uuid4(),
        username=username,
        email=f"{username}@correo.com",
        first_name="Ana",
        paternal_surname="Ríos",
        maternal_surname=None,
    )


def test_devuelve_el_perfil_de_quien_pide() -> None:
    ana, luis = _profile("ana.rios"), _profile("luis.paz")
    get_my_profile = GetMyProfile(InMemoryProfileGateway(ana, luis))

    assert get_my_profile.execute(ana.id) == ana
    assert get_my_profile.execute(luis.id) == luis


def test_cuenta_que_ya_no_existe_es_sesion_no_valida() -> None:
    """Carrera con una eliminación: se responde como una sesión que ya no vale."""
    get_my_profile = GetMyProfile(InMemoryProfileGateway())

    with pytest.raises(ProfileNotFoundError) as error:
        get_my_profile.execute(uuid.uuid4())

    # Mismo código que el resto de la API: la app vuelve al login (D56).
    assert error.value.code == "not_authenticated"
