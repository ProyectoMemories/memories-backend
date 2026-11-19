"""Carga la lista de contraseñas comunes que rechaza PasswordPolicy (D62-B)."""

from functools import lru_cache
from pathlib import Path

_COMMON_PASSWORDS_FILE = Path(__file__).with_name("common_passwords.txt")


@lru_cache
def load_common_passwords() -> frozenset[str]:
    lines = _COMMON_PASSWORDS_FILE.read_text(encoding="utf-8").splitlines()
    return frozenset(line for line in lines if line and not line.startswith("#"))
