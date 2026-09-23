"""Validacion de las imagenes que llegan a la API.

No basta con creer al cliente: el content-type se puede falsear. Se comprueba
tambien la firma binaria del archivo, que es lo que de verdad dice que formato
es. Sin dependencias externas: son tres formatos y sus cabeceras son fijas.
"""

from dataclasses import dataclass

from app.modules.memories.domain.errors import InvalidImageError

EXTENSION_BY_CONTENT_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


@dataclass(frozen=True, slots=True)
class PhotoUploadRules:
    allowed_content_types: frozenset[str]
    max_size_bytes: int


def _matches_signature(data: bytes, content_type: str) -> bool:
    if content_type == "image/jpeg":
        return data.startswith(b"\xff\xd8\xff")
    if content_type == "image/png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    return False


def validate_image(data: bytes, content_type: str, rules: PhotoUploadRules) -> str:
    """Devuelve la extension del archivo si la imagen es aceptable."""
    normalized = (content_type or "").split(";")[0].strip().lower()

    if not data:
        raise InvalidImageError("El archivo esta vacio.")
    if normalized not in rules.allowed_content_types:
        permitidos = ", ".join(sorted(rules.allowed_content_types))
        raise InvalidImageError(f"Formato no admitido. Se aceptan: {permitidos}.")
    if len(data) > rules.max_size_bytes:
        limite_mb = rules.max_size_bytes / (1024 * 1024)
        raise InvalidImageError(f"La imagen pasa del limite de {limite_mb:.0f} MB.")
    if not _matches_signature(data, normalized):
        raise InvalidImageError("El archivo no es una imagen del formato que declara.")

    return EXTENSION_BY_CONTENT_TYPE.get(normalized, ".bin")
