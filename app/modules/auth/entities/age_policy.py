"""Edad mínima para registrarse (RN-08). La base no la impone: cambia con el tiempo."""

from datetime import date

from app.shared.entities.errors import BusinessRuleError

MIN_AGE_YEARS = 14


class UnderageError(BusinessRuleError):
    code = "underage"
    message = f"Necesitas tener al menos {MIN_AGE_YEARS} años para registrarte."


def age_on(birth_date: date, today: date) -> int:
    had_birthday = (today.month, today.day) >= (birth_date.month, birth_date.day)
    return today.year - birth_date.year - (0 if had_birthday else 1)


def ensure_minimum_age(birth_date: date, today: date) -> None:
    if age_on(birth_date, today) < MIN_AGE_YEARS:
        raise UnderageError
