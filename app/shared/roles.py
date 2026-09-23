"""Roles del sistema.

Solo hay dos y son estables, asi que viven en el nucleo compartido: los usa el
dominio de usuarios, la autenticacion y las dependencias de la API.
"""

from enum import StrEnum


class UserRole(StrEnum):
    USER = "user"
    SUPERUSER = "superuser"
