"""Configuración de la API, leída solo de variables de entorno (CLAUDE.md §10)."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Lo mínimo para conectarse a la base. Lo usan la API y Alembic."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Formato: postgresql+psycopg://usuario:clave@host:puerto/base
    database_url: str

    @field_validator("database_url")
    @classmethod
    def _psycopg_driver(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("debe empezar con postgresql+psycopg://")
        return value


class Settings(DatabaseSettings):
    app_env: Literal["development", "test", "production"] = "development"

    # Único origen al que CORS deja llamar a la API: el de la app web
    # (CLAUDE.md §9). Es obligatorio para que nadie despliegue sin pensarlo.
    # También es la base de los enlaces que van en los correos.
    web_app_origin: str

    # Firma los tokens (JWT de acceso y enlaces de los correos). Larga y
    # aleatoria; nunca la misma en desarrollo y en producción.
    secret_key: str = Field(min_length=32)

    # Versión vigente de la política de privacidad que se acepta al registrarse
    # (RN-50). El texto de la política está pendiente (P27).
    privacy_policy_version: str = Field(min_length=1, max_length=50)

    # Correo saliente. En desarrollo apunta a Mailpit (D62-C).
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    email_from: str = "Memories <no-reply@memories.local>"

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
