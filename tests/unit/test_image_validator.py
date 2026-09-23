"""No basta con creer al content-type que declara el cliente."""

import pytest

from app.modules.memories.application.image_validator import PhotoUploadRules, validate_image
from app.modules.memories.domain.errors import InvalidImageError

REGLAS = PhotoUploadRules(
    allowed_content_types=frozenset({"image/jpeg", "image/png", "image/webp"}),
    max_size_bytes=1024,
)

JPEG = b"\xff\xd8\xff" + b"0" * 32
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32
WEBP = b"RIFF" + b"0000" + b"WEBP" + b"0" * 32


@pytest.mark.parametrize(
    ("data", "content_type", "extension"),
    [(JPEG, "image/jpeg", ".jpg"), (PNG, "image/png", ".png"), (WEBP, "image/webp", ".webp")],
)
def test_acepta_los_formatos_permitidos(data: bytes, content_type: str, extension: str) -> None:
    assert validate_image(data, content_type, REGLAS) == extension


def test_rechaza_un_formato_no_permitido() -> None:
    with pytest.raises(InvalidImageError):
        validate_image(b"GIF89a", "image/gif", REGLAS)


def test_rechaza_un_archivo_que_miente_sobre_su_formato() -> None:
    with pytest.raises(InvalidImageError):
        validate_image(b"esto es texto plano", "image/png", REGLAS)


def test_rechaza_un_archivo_vacio() -> None:
    with pytest.raises(InvalidImageError):
        validate_image(b"", "image/png", REGLAS)


def test_rechaza_un_archivo_demasiado_grande() -> None:
    with pytest.raises(InvalidImageError):
        validate_image(PNG + b"0" * 2048, "image/png", REGLAS)
