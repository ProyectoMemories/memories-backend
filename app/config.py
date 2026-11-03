"""Configuración de la API, leída solo de variables de entorno (CLAUDE.md §10)."""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"

    # Único origen al que CORS deja llamar a la API: el de la app web
    # (CLAUDE.md §9). Es obligatorio para que nadie despliegue sin pensarlo.
    web_app_origin: str

    @field_validator("web_app_origin")
    @classmethod
    def _single_explicit_origin(cls, value: str) -> str:
        if value == "*" or "," in value:
            raise ValueError("debe ser un solo origen, nunca '*'")
        if not value.startswith(("http://", "https://")):
            raise ValueError("debe empezar con http:// o https://")
        if value.endswith("/"):
            raise ValueError("no debe terminar en '/': el navegador lo compara exacto")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # los valores vienen del entorno
