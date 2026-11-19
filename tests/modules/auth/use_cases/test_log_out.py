from app.modules.auth.entities.user_session import ClientPlatform
from app.modules.auth.use_cases.log_in import LogInInput
from app.modules.auth.use_cases.log_out import LogOutInput
from tests.modules.auth.use_cases.conftest import PASSWORD, AuthKit

ANDROID = ClientPlatform.ANDROID


def _revoked(kit: AuthKit) -> list[bool]:
    return [s.revoked_at is not None for s in kit.sessions.sessions.values()]


def test_revoca_la_sesion_y_repetir_no_falla(kit: AuthKit) -> None:
    kit.add_user()
    issued = kit.log_in().execute(LogInInput("ana.rios", PASSWORD, ANDROID, None))

    kit.log_out().execute(LogOutInput(issued.refresh_token, ANDROID))
    kit.log_out().execute(LogOutInput(issued.refresh_token, ANDROID))

    assert _revoked(kit) == [True]


def test_sin_token_o_con_token_ajeno_no_revoca_nada(kit: AuthKit) -> None:
    kit.add_user()
    issued = kit.log_in().execute(LogInInput("ana.rios", PASSWORD, ANDROID, None))
    session_id = issued.refresh_token.split(".")[0]

    for token in (None, "basura", f"{session_id}.otro-secreto"):
        kit.log_out().execute(LogOutInput(token, ANDROID))

    assert _revoked(kit) == [False]
