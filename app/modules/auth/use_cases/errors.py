"""Errores de los casos de uso de auth (credenciales, enlaces y sesiones)."""

from app.shared.entities.errors import InvalidRequestError, UnauthorizedError


class ExpiredLinkError(InvalidRequestError):
    code = "expired_token"
    message = "El enlace venció. Pide uno nuevo."


class InvalidLinkError(InvalidRequestError):
    code = "invalid_token"
    message = "El enlace no es válido. Pide uno nuevo."


class InvalidCredentialsError(UnauthorizedError):
    code = "invalid_credentials"
    # Igual exista o no la cuenta (design.md §6).
    message = "El usuario o la contraseña no son correctos."


class InvalidRefreshTokenError(UnauthorizedError):
    code = "invalid_refresh_token"
    message = "Tu sesión terminó. Vuelve a iniciar sesión."


class NotAuthenticatedError(UnauthorizedError):
    code = "not_authenticated"
    message = "Necesitas iniciar sesión."


class AccessTokenExpiredError(NotAuthenticatedError):
    # La app renueva el token solo con este código (design.md §2).
    code = "access_token_expired"
    message = "Tu token de acceso venció."
