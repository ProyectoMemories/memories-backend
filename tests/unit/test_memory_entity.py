"""Reglas de negocio del recuerdo. Sin base de datos ni framework."""

import uuid
from datetime import date, timedelta

import pytest

from app.modules.memories.domain.entities.memory import Memory
from app.modules.memories.domain.entities.photo import Photo
from app.modules.memories.domain.errors import (
    InvalidMemoryTitleError,
    InvalidMomentDateError,
    MemoryNeedsAtLeastOnePhotoError,
    PhotoNotOwnedError,
    TooManyPhotosError,
)

OWNER = uuid.uuid4()
HOY = date(2026, 9, 22)


def una_foto(owner_id: uuid.UUID = OWNER) -> Photo:
    return Photo.register(
        owner_id=owner_id,
        storage_key=f"{owner_id}/{uuid.uuid4().hex}.jpg",
        content_type="image/jpeg",
        size_bytes=1024,
        checksum_sha256="a" * 64,
    )


def crear(**kwargs: object) -> Memory:
    argumentos: dict = {
        "owner_id": OWNER,
        "title": "Viaje a Paracas",
        "moment_date": HOY - timedelta(days=30),
        "photos": [una_foto()],
        "max_photos": 10,
        "today": HOY,
    }
    argumentos.update(kwargs)
    return Memory.create(**argumentos)  # type: ignore[arg-type]


def test_un_recuerdo_necesita_al_menos_una_fotografia() -> None:
    with pytest.raises(MemoryNeedsAtLeastOnePhotoError):
        crear(photos=[])


def test_el_titulo_no_puede_estar_vacio() -> None:
    with pytest.raises(InvalidMemoryTitleError):
        crear(title="   ")


def test_no_se_puede_recordar_el_futuro() -> None:
    with pytest.raises(InvalidMomentDateError):
        crear(moment_date=HOY + timedelta(days=1))


def test_no_se_admiten_mas_fotografias_que_el_maximo() -> None:
    with pytest.raises(TooManyPhotosError):
        crear(photos=[una_foto() for _ in range(4)], max_photos=3)


def test_las_fotografias_son_de_quien_crea_el_recuerdo() -> None:
    with pytest.raises(PhotoNotOwnedError):
        crear(photos=[una_foto(owner_id=uuid.uuid4())])


def test_al_crear_las_fotografias_quedan_asociadas_y_ordenadas() -> None:
    fotos = [una_foto(), una_foto(), una_foto()]
    recuerdo = crear(photos=fotos)

    assert [foto.position for foto in recuerdo.photos] == [0, 1, 2]
    assert all(foto.memory_id == recuerdo.id for foto in recuerdo.photos)


def test_quitar_la_ultima_fotografia_no_esta_permitido() -> None:
    recuerdo = crear()
    with pytest.raises(MemoryNeedsAtLeastOnePhotoError):
        recuerdo.remove_photo(recuerdo.photos[0].id)


def test_quitar_una_fotografia_reordena_el_resto() -> None:
    recuerdo = crear(photos=[una_foto(), una_foto(), una_foto()])
    primera = recuerdo.photos[0]

    quitada = recuerdo.remove_photo(primera.id)

    assert quitada.memory_id is None
    assert recuerdo.photo_count == 2
    assert [foto.position for foto in recuerdo.photos] == [0, 1]


def test_la_descripcion_vacia_se_guarda_como_ausente() -> None:
    recuerdo = crear(description="   ")
    assert recuerdo.description is None
