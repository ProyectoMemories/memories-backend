"""Configuracion de la aplicacion.

Todo se lee de variables de entorno (o del .env en local). Los secretos no
tienen valor por defecto a proposito: si falta uno, la app no arranca en vez
de arrancar con una credencial conocida.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Aplicacion ──────────────────────────────────────────────────
    APP_NAME: str = "Memories API"
    APP_VERSION: str = "0.1.0"
    ENV: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"
    # La documentacion interactiva describe todos los endpoints y sus esquemas;
    # fuera de local se responde 404 para no publicarla.
    DOCS_LOCAL_ONLY: bool = True
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080"

    # ─── Base de datos ───────────────────────────────────────────────
    DATABASE_URL: str
    # Esquema de Postgres. Vacio = el predeterminado de la base, que es lo que
    # usan desarrollo y produccion. Los tests lo fijan a memories_test para
    # aislarse sin necesidad de otra base de datos.
    DB_SCHEMA: str | None = None
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 5
    DATABASE_POOL_TIMEOUT: int = 30

    # ─── Redis / cache ───────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_PROVIDER: Literal["redis", "memory"] = "redis"

    # ─── Seguridad (RNF-08) ──────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # El valor es el nombre de un algoritmo, no una contrasena.
    PASSWORD_HASHING_SCHEME: Literal["bcrypt", "argon2"] = "bcrypt"  # noqa: S105
    BCRYPT_ROUNDS: int = 12
    ARGON2_TIME_COST: int = 3
    ARGON2_MEMORY_COST: int = 65536
    ARGON2_PARALLELISM: int = 4

    RATE_LIMIT_AUTH_PER_MINUTE: int = 10
    RATE_LIMIT_DEFAULT_PER_MINUTE: int = 120

    # ─── Almacenamiento de fotografias (RNF-09) ──────────────────────
    STORAGE_PROVIDER: Literal["minio", "s3", "local"] = "minio"
    S3_BUCKET: str = "memories-photos"
    S3_REGION: str = "us-east-1"
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None
    S3_ENDPOINT_URL: str | None = None
    S3_PUBLIC_ENDPOINT: str | None = None
    S3_USE_SSL: bool = False
    S3_PRESIGNED_URL_TTL_SECONDS: int = 900
    LOCAL_STORAGE_PATH: str = "./storage"

    # ─── Reglas de producto ──────────────────────────────────────────
    MAX_PHOTOS_PER_MEMORY: int = 10
    MAX_PHOTO_SIZE_MB: int = 15
    ALLOWED_IMAGE_CONTENT_TYPES: str = "image/jpeg,image/png,image/webp"

    # ─── Logging ─────────────────────────────────────────────────────
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "console"] = "json"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_image_content_types(self) -> set[str]:
        return {
            item.strip().lower()
            for item in self.ALLOWED_IMAGE_CONTENT_TYPES.split(",")
            if item.strip()
        }

    @property
    def max_photo_size_bytes(self) -> int:
        return self.MAX_PHOTO_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.ENV == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
