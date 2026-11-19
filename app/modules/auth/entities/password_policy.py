"""Reglas de la contraseña (D62-B): largo y que no sea común, sin composición."""

from collections.abc import Collection

from app.shared.entities.errors import BusinessRuleError

MIN_LENGTH = 8
MAX_LENGTH = 64


class PasswordLengthError(BusinessRuleError):
    code = "password_length"
    message = f"La contraseña debe tener entre {MIN_LENGTH} y {MAX_LENGTH} caracteres."


class PasswordTooCommonError(BusinessRuleError):
    code = "password_too_common"
    message = "Esa contraseña es muy común. Elige otra."


class PasswordPolicy:
    def __init__(self, common_passwords: Collection[str]) -> None:
        # La lista viene en minúsculas; se compara sin importar mayúsculas.
        self._common_passwords = common_passwords

    def ensure_acceptable(self, password: str) -> None:
        if not MIN_LENGTH <= len(password) <= MAX_LENGTH:
            raise PasswordLengthError
        if password.lower() in self._common_passwords:
            raise PasswordTooCommonError
