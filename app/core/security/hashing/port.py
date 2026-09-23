"""Contrato de hashing de contrasenas (RNF-08).

Cambiar de algoritmo es cambiar una variable de entorno, no tocar codigo:
quien consume esto solo conoce esta interfaz.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class PasswordHasher(Protocol):
    """Un algoritmo concreto de hashing."""

    scheme: str

    def identifies(self, hashed: str) -> bool:
        """True si este hash fue generado por este algoritmo."""
        ...

    def hash(self, plain: str) -> str: ...

    def verify(self, plain: str, hashed: str) -> bool: ...

    def needs_rehash(self, hashed: str) -> bool:
        """True si el hash sigue siendo valido pero usa parametros antiguos."""
        ...
