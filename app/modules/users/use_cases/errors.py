"""Errores de los casos de uso de users."""

from app.shared.entities.errors import UnauthorizedError


class ProfileNotFoundError(UnauthorizedError):
    # La cuenta desapareció después de autenticarse (se eliminó en ese
    # instante): para la app es lo mismo que una sesión que ya no vale, así
    # que usa el mismo código que auth (design.md §2).
    code = "not_authenticated"
    message = "Necesitas iniciar sesión."
