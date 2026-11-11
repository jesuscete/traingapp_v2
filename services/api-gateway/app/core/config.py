from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-secret-change-me-0123456789abcdef"
DEV_INTERNAL_TOKEN = "internal-dev-token"
DEV_DB_CREDENTIALS = "traingapp:traingapp@"
MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

    app_name: str = "api-gateway"
    app_env: str = "development"
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = (
        "postgresql+asyncpg://traingapp:traingapp@localhost:5432/traingapp"
    )
    jwt_secret: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    internal_token: str = DEV_INTERNAL_TOKEN
    ai_parser_url: str = "http://localhost:8100"
    chat_draft_ttl_seconds: int = 1800
    live_session_ttl_seconds: int = 14400
    plan_session_ttl_seconds: int = 3600
    # Base de las imágenes de free-exercise-db (rutas relativas del catálogo).
    exercise_image_base_url: str = (
        "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/exercises/"
    )
    # Orígenes separados por comas (p. ej. añadir http://192.168.1.50:3000 para el móvil).
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _reject_dev_secrets_in_production(self) -> Self:
        if self.app_env != "production":
            return self
        problems: list[str] = []
        if self.jwt_secret == DEV_JWT_SECRET or len(self.jwt_secret) < MIN_SECRET_LENGTH:
            problems.append(f"APP_JWT_SECRET (default o < {MIN_SECRET_LENGTH} caracteres)")
        if (
            self.internal_token == DEV_INTERNAL_TOKEN
            or len(self.internal_token) < MIN_SECRET_LENGTH
        ):
            problems.append(f"APP_INTERNAL_TOKEN (default o < {MIN_SECRET_LENGTH} caracteres)")
        if DEV_DB_CREDENTIALS in self.database_url:
            problems.append("APP_DATABASE_URL (credenciales de desarrollo)")
        if problems:
            raise ValueError("Secretos inseguros en producción: " + ", ".join(problems))
        return self


settings = Settings()
