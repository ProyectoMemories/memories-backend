import uuid

import pytest

from app.modules.auth.use_cases.ports import TokenInvalidError
from app.modules.auth.use_cases.refresh_token import (
    format_refresh_token,
    parse_refresh_token,
)

SESSION_ID = uuid.UUID("01900000-0000-7000-8000-000000000002")


def test_ida_y_vuelta() -> None:
    token = format_refresh_token(SESSION_ID, "secreto")

    assert parse_refresh_token(token) == (SESSION_ID, "secreto")


@pytest.mark.parametrize(
    "token", ["", "sin-punto", "no-es-uuid.secreto", f"{SESSION_ID}."]
)
def test_mal_formado(token: str) -> None:
    with pytest.raises(TokenInvalidError):
        parse_refresh_token(token)
