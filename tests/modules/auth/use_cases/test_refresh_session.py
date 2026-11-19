import pytest

from app.modules.auth.entities.user import AccountStatus
from app.modules.auth.entities.user_session import ClientPlatform
from app.modules.auth.use_cases.errors import InvalidRefreshTokenError
from app.modules.auth.use_cases.log_in import LogInInput
from app.modules.auth.use_cases.refresh_session import RefreshSessionInput
from app.modules.auth.use_cases.token_issuer import IssuedTokens
from tests.modules.auth.use_cases.conftest import PASSWORD, AuthKit

ANDROID = ClientPlatform.ANDROID


def _log_in(kit: AuthKit) -> IssuedTokens:
    kit.add_user()
    return kit.log_in().execute(LogInInput("ana.rios", PASSWORD, ANDROID, None))


def _refresh(
    kit: AuthKit, token: str | None, platform: ClientPlatform = ANDROID
) -> IssuedTokens:
    return kit.refresh_session().execute(RefreshSessionInput(token, platform))


def test_rota_el_token_en_la_misma_sesion(kit: AuthKit) -> None:
    first = _log_in(kit)

    second = _refresh(kit, first.refresh_token)

    session_id = first.refresh_token.split(".")[0]
    assert second.refresh_token == f"{session_id}.secret-2"


def test_reusar_un_token_rotado_revoca_la_sesion(kit: AuthKit) -> None:
    first = _log_in(kit)
    second = _refresh(kit, first.refresh_token)

    with pytest.raises(InvalidRefreshTokenError):
        _refresh(kit, first.refresh_token)

    [user_session] = kit.sessions.sessions.values()
    assert user_session.revoked_at is not None
    with pytest.raises(InvalidRefreshTokenError):
        _refresh(kit, second.refresh_token)


@pytest.mark.parametrize(
    "token", [None, "basura", "0193b0a0-0000-7000-8000-000000000000.x"]
)
def test_token_ausente_o_inventado(kit: AuthKit, token: str | None) -> None:
    with pytest.raises(InvalidRefreshTokenError):
        _refresh(kit, token)


def test_un_token_de_android_no_sirve_por_el_canal_web(kit: AuthKit) -> None:
    first = _log_in(kit)

    with pytest.raises(InvalidRefreshTokenError):
        _refresh(kit, first.refresh_token, ClientPlatform.WEB)


def test_cuenta_que_dejo_de_estar_activa(kit: AuthKit) -> None:
    first = _log_in(kit)
    user = kit.users.get_by_login("ana.rios")
    assert user is not None
    user.status = AccountStatus.SUSPENDED
    kit.users.save(user)

    with pytest.raises(InvalidRefreshTokenError):
        _refresh(kit, first.refresh_token)
