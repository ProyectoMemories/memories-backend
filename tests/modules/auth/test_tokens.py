import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.modules.auth.tokens import (
    ExpiredTokenError,
    InvalidTokenError,
    TokenPurpose,
    create_email_token,
    read_email_token,
)

SECRET = "clave-solo-para-pruebas-con-mas-de-32-caracteres"
USER_ID = uuid.UUID("01900000-0000-7000-8000-000000000001")


def _token(lifetime: timedelta = timedelta(hours=1), secret: str = SECRET) -> str:
    return create_email_token(
        USER_ID, TokenPurpose.VERIFY_EMAIL, lifetime, secret, datetime.now(UTC)
    )


def test_token_vigente_devuelve_el_usuario() -> None:
    assert read_email_token(_token(), TokenPurpose.VERIFY_EMAIL, SECRET) == USER_ID


def test_token_vencido_se_rechaza() -> None:
    with pytest.raises(ExpiredTokenError):
        read_email_token(
            _token(lifetime=timedelta(seconds=-1)), TokenPurpose.VERIFY_EMAIL, SECRET
        )


def test_token_alterado_se_rechaza() -> None:
    header, _, signature = _token().split(".")
    other_user = create_email_token(
        uuid.uuid4(),
        TokenPurpose.VERIFY_EMAIL,
        timedelta(hours=1),
        SECRET,
        datetime.now(UTC),
    )
    # Se cambia el usuario del contenido y se deja la firma original.
    tampered = f"{header}.{other_user.split('.')[1]}.{signature}"

    with pytest.raises(InvalidTokenError):
        read_email_token(tampered, TokenPurpose.VERIFY_EMAIL, SECRET)


def test_token_firmado_con_otra_clave_se_rechaza() -> None:
    other = "otra-clave-distinta-con-mas-de-32-caracteres!!"
    with pytest.raises(InvalidTokenError):
        read_email_token(_token(secret=other), TokenPurpose.VERIFY_EMAIL, SECRET)


def test_token_de_otro_proposito_se_rechaza() -> None:
    claims = {
        "sub": str(USER_ID),
        "purpose": "reset_password",
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }
    token = jwt.encode(claims, SECRET, algorithm="HS256")

    with pytest.raises(InvalidTokenError):
        read_email_token(token, TokenPurpose.VERIFY_EMAIL, SECRET)
