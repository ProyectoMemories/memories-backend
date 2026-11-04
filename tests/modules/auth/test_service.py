"""Reglas del servicio que no necesitan base de datos."""

from datetime import date

import pytest

from app.modules.auth.service import age_on


@pytest.mark.parametrize(
    ("birth_date", "today", "age"),
    [
        (date(2012, 11, 3), date(2026, 11, 3), 14),  # cumple hoy
        (date(2012, 11, 4), date(2026, 11, 3), 13),  # cumple mañana
        (date(2008, 2, 29), date(2026, 2, 28), 17),  # nacido un 29 de febrero
        (date(2008, 2, 29), date(2026, 3, 1), 18),
    ],
)
def test_edad(birth_date: date, today: date, age: int) -> None:
    assert age_on(birth_date, today) == age
