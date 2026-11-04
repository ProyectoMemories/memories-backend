import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.modules.auth.tokens import (
    ExpiredTokenError,
    InvalidTokenError,
    TokenPurpose,
    create_access_token,
    create_email_token,
    format_refresh_token,
    hash_refresh_secret,
    new_refresh_secret,
    parse_refresh_token,
    read_access_token,
    read_email_token,
    refresh_secret_matches,
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


# ─── Token de acceso ───────────────────────────────────────────────────────

SESSION_ID = uuid.UUID("01900000-0000-7000-8000-000000000002")


def _access(lifetime: timedelta = timedelta(minutes=15)) -> str:
    return create_access_token(USER_ID, SESSION_ID, lifetime, SECRET, datetime.now(UTC))


def test_token_de_acceso_vigente() -> None:
    assert read_access_token(_access(), SECRET) == (USER_ID, SESSION_ID)
    claims = jwt.decode(_access(), SECRET, algorithms=["HS256"])
    assert claims["type"] == "access"
    assert claims["exp"] - claims["iat"] == 15 * 60


def test_token_de_acceso_vencido() -> None:
    with pytest.raises(ExpiredTokenError):
        read_access_token(_access(timedelta(seconds=-1)), SECRET)


def test_token_de_acceso_alterado() -> None:
    header, payload, signature = _access().split(".")
    with pytest.raises(InvalidTokenError):
        read_access_token(f"{header}.{payload}.{signature[::-1]}", SECRET)


@pytest.mark.parametrize("token_type", [None, "refresh", "ACCESS"])
def test_token_sin_tipo_access_no_sirve_como_acceso(token_type: str | None) -> None:
    claims = {
        "sub": str(USER_ID),
        "sid": str(SESSION_ID),
        "exp": datetime.now(UTC) + timedelta(minutes=15),
    }
    if token_type is not None:
        claims["type"] = token_type

    with pytest.raises(InvalidTokenError):
        read_access_token(jwt.encode(claims, SECRET, algorithm="HS256"), SECRET)


def test_enlace_de_verificacion_no_sirve_como_acceso_ni_al_reves() -> None:
    with pytest.raises(InvalidTokenError):
        read_access_token(_token(), SECRET)
    with pytest.raises(InvalidTokenError):
        read_email_token(_access(), TokenPurpose.VERIFY_EMAIL, SECRET)


# ─── Token de renovación ───────────────────────────────────────────────────


def test_token_de_renovacion_ida_y_vuelta() -> None:
    secret = new_refresh_secret()
    token = format_refresh_token(SESSION_ID, secret)

    assert parse_refresh_token(token) == (SESSION_ID, secret)
    assert refresh_secret_matches(secret, hash_refresh_secret(secret))
    assert not refresh_secret_matches(new_refresh_secret(), hash_refresh_secret(secret))
    assert hash_refresh_secret(secret) != secret


@pytest.mark.parametrize(
    "token", ["", "sin-punto", "no-es-uuid.secreto", f"{SESSION_ID}."]
)
def test_token_de_renovacion_mal_formado(token: str) -> None:
    with pytest.raises(InvalidTokenError):
        parse_refresh_token(token)
