"""Servicio de hashing con algoritmo intercambiable (RNF-08).

Guarda un algoritmo *principal* (el que se usa para hashear) y un registro de
todos los conocidos (los que se usan para verificar). Gracias a eso, cambiar
PASSWORD_HASHING_SCHEME no invalida ninguna contrasena existente: el hash
antiguo se sigue verificando con su algoritmo y se vuelve a hashear con el
nuevo en el siguiente inicio de sesion (ver needs_rehash).
"""

from collections.abc import Sequence

from app.core.security.hashing.port import PasswordHasher


class PasswordHashingService:
    def __init__(self, primary: PasswordHasher, known: Sequence[PasswordHasher]) -> None:
        self._primary = primary
        self._known = list(known)

    @property
    def scheme(self) -> str:
        return self._primary.scheme

    def hash(self, plain: str) -> str:
        return self._primary.hash(plain)

    def verify(self, plain: str, hashed: str) -> bool:
        hasher = self._resolve(hashed)
        if hasher is None:
            return False
        return hasher.verify(plain, hashed)

    def needs_rehash(self, hashed: str) -> bool:
        """True si conviene volver a hashear: otro algoritmo u otros parametros."""
        hasher = self._resolve(hashed)
        if hasher is None:
            return True
        if hasher.scheme != self._primary.scheme:
            return True
        return hasher.needs_rehash(hashed)

    def _resolve(self, hashed: str) -> PasswordHasher | None:
        for hasher in self._known:
            if hasher.identifies(hashed):
                return hasher
        return None
