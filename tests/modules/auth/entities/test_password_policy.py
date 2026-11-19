import pytest

from app.modules.auth.entities.password_policy import (
    PasswordLengthError,
    PasswordPolicy,
    PasswordTooCommonError,
)

policy = PasswordPolicy(common_passwords={"password", "contrasena"})


@pytest.mark.parametrize(
    "password",
    [
        "a" * 7 + "Z",  # 8: el mínimo
        "q" * 64,  # 64: el máximo
        "solo letras minusculas",  # sin reglas de composición (D62-B)
    ],
)
def test_contrasenas_aceptadas(password: str) -> None:
    policy.ensure_acceptable(password)


@pytest.mark.parametrize("password", ["x7Kp2mQ", "q" * 65])
def test_largo_fuera_de_rango(password: str) -> None:
    with pytest.raises(PasswordLengthError):
        policy.ensure_acceptable(password)


@pytest.mark.parametrize("password", ["password", "PassWord", "Contrasena"])
def test_comun_sin_importar_mayusculas(password: str) -> None:
    with pytest.raises(PasswordTooCommonError):
        policy.ensure_acceptable(password)
