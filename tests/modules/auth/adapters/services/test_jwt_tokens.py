import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.modules.auth.adapters.services.jwt_tokens import (
    JwtAccessTokens,
    JwtEmailLinkTokens,
    JwtPasswordResetTokens,
)
from app.modules.auth.use_cases.ports import (
    TokenExpiredError,
    TokenInvalidError,
    TokenPurpose,
)

SECRET = "clave-solo-para-pruebas-con-mas-de-32-caracteres"
USER_ID = uuid.UUID("01900000-0000-7000-8000-000000000001")
SESSION_ID = uuid.UUID("01900000-0000-7000-8000-000000000002")
links = JwtEmailLinkTokens(SECRET)
access = JwtAccessTokens(SECRET)
VERIFY = TokenPurpose.VERIFY_EMAIL


def _link(
    lifetime: timedelta = timedelta(hours=1), user_id: uuid.UUID = USER_ID
) -> str:
    return links.create(user_id, VERIFY, lifetime, datetime.now(UTC))


def _access(lifetime: timedelta = timedelta(minutes=15)) -> str:
    return access.create(USER_ID, SESSION_ID, lifetime, datetime.now(UTC))


# ─── Enlaces de correo ─────────────────────────────────────────────────────


def test_enlace_vigente_devuelve_el_usuario() -> None:
    assert links.read(_link(), VERIFY) == USER_ID


def test_enlace_vencido() -> None:
    with pytest.raises(TokenExpiredError):
        links.read(_link(timedelta(seconds=-1)), VERIFY)


def test_enlace_alterado() -> None:
    header, _, signature = _link().split(".")
    other_payload = _link(user_id=uuid.uuid4()).split(".")[1]

    with pytest.raises(TokenInvalidError):
        links.read(f"{header}.{other_payload}.{signature}", VERIFY)


def test_enlace_firmado_con_otra_clave() -> None:
    other = JwtEmailLinkTokens("otra-clave-distinta-con-mas-de-32-caracteres!!")
    token = other.create(USER_ID, VERIFY, timedelta(hours=1), datetime.now(UTC))

    with pytest.raises(TokenInvalidError):
        links.read(token, VERIFY)


def test_enlace_de_otro_proposito() -> None:
    claims = {
        "sub": str(USER_ID),
        "purpose": "reset_password",
        "exp": datetime.now(UTC) + timedelta(hours=1),
    }

    with pytest.raises(TokenInvalidError):
        links.read(jwt.encode(claims, SECRET, algorithm="HS256"), VERIFY)


# ─── Token de acceso ───────────────────────────────────────────────────────


def test_token_de_acceso_vigente() -> None:
    token = _access()

    assert access.read(token) == (USER_ID, SESSION_ID)
    claims = jwt.decode(token, SECRET, algorithms=["HS256"])
    assert claims["type"] == "access"
    assert claims["exp"] - claims["iat"] == 15 * 60


def test_token_de_acceso_vencido() -> None:
    with pytest.raises(TokenExpiredError):
        access.read(_access(timedelta(seconds=-1)))


def test_token_de_acceso_alterado() -> None:
    header, payload, signature = _access().split(".")

    with pytest.raises(TokenInvalidError):
        access.read(f"{header}.{payload}.{signature[::-1]}")


@pytest.mark.parametrize("token_type", [None, "refresh", "ACCESS"])
def test_sin_type_access_no_sirve_como_acceso(token_type: str | None) -> None:
    claims: dict[str, object] = {
        "sub": str(USER_ID),
        "sid": str(SESSION_ID),
        "exp": datetime.now(UTC) + timedelta(minutes=15),
    }
    if token_type is not None:
        claims["type"] = token_type

    with pytest.raises(TokenInvalidError):
        access.read(jwt.encode(claims, SECRET, algorithm="HS256"))


def test_un_enlace_no_sirve_como_acceso_ni_al_reves() -> None:
    with pytest.raises(TokenInvalidError):
        access.read(_link())
    with pytest.raises(TokenInvalidError):
        links.read(_access(), VERIFY)


# ─── Enlace de recuperación ────────────────────────────────────────────────

resets = JwtPasswordResetTokens(SECRET)
CHANGED_AT = datetime(2026, 11, 19, 12, 0, 0, 123456, tzinfo=UTC)


def _reset(
    changed_at: datetime | None = CHANGED_AT,
    lifetime: timedelta = timedelta(minutes=30),
) -> str:
    return resets.create(USER_ID, changed_at, lifetime, datetime.now(UTC))


def test_enlace_de_recuperacion_trae_la_fecha_exacta() -> None:
    assert resets.read(_reset()) == (USER_ID, CHANGED_AT)
    assert resets.read(_reset(changed_at=None)) == (USER_ID, None)


def test_enlace_de_recuperacion_vencido() -> None:
    with pytest.raises(TokenExpiredError):
        resets.read(_reset(lifetime=timedelta(seconds=-1)))


def test_verificacion_y_recuperacion_no_se_confunden() -> None:
    with pytest.raises(TokenInvalidError):
        resets.read(_link())
    with pytest.raises(TokenInvalidError):
        links.read(_reset(), VERIFY)
    with pytest.raises(TokenInvalidError):
        access.read(_reset())
