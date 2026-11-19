from datetime import date

import pytest

from app.modules.auth.entities.age_policy import (
    UnderageError,
    age_on,
    ensure_minimum_age,
)


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


def test_con_14_anos_puede_registrarse() -> None:
    ensure_minimum_age(date(2012, 11, 3), date(2026, 11, 3))


def test_con_13_anos_no_puede_registrarse() -> None:
    with pytest.raises(UnderageError):
        ensure_minimum_age(date(2012, 11, 4), date(2026, 11, 3))
