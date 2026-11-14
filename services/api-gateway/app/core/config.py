from typing import Literal, Self

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
    # Token de acceso corto; la sesión se mantiene con el refresh token rotatorio.
    access_token_expire_minutes: int = 15
    remember_token_expire_days: int = 30  # refresh con «Recuérdame»
    session_refresh_hours: int = 12  # refresh sin «Recuérdame»
    internal_token: str = DEV_INTERNAL_TOKEN
    ai_parser_url: str = "http://localhost:8100"
    # Debe cubrir el timeout del LLM en ai-parser (90 s) más un reintento de reparación.
    ai_parser_timeout_seconds: float = 200
    # M10: "rules" = generador de planes por árbol de decisión (sin IA, por defecto);
    # "llm" = generación anterior con Claude (splits + plan) y relleno determinista.
    plan_engine: Literal["rules", "llm"] = "rules"
    # Nodos deterministas del chat activos (delante del agente). Quitar uno = ese tipo de
    # mensaje vuelve al agente con IA, sin desplegar nada.
    chat_rule_nodes: str = "guided,routine,fatigue,nutrition,alternatives,recommend"
    chat_draft_ttl_seconds: int = 1800
    live_session_ttl_seconds: int = 14400
    plan_session_ttl_seconds: int = 3600
    # Bases de alimentos (M5). USDA: clave gratuita en api.data.gov (DEMO_KEY = muy limitada).
    off_base_url: str = "https://es.openfoodfacts.org"
    # Buscador nuevo de OFF (search-a-licious): admite filtros por tienda y pais.
    off_search_url: str = "https://search.openfoodfacts.org"
    # Busqueda remota en OFF cuando hay pocos resultados locales. Desactivada mientras la
    # base local (importacion Lidl) cubre lo habitual: OFF es lento y mete ruido.
    off_remote_search: bool = False
    usda_base_url: str = "https://api.nal.usda.gov/fdc/v1"
    usda_api_key: str = "DEMO_KEY"
    # M10: las comidas por texto usan el diccionario propio (+ OFF); USDA apagado.
    usda_enabled: bool = False
    food_api_timeout_seconds: float = 8
    # Garmin (M6.2): API personal oficial; sondeo periódico (0 = desactivado).
    garmin_base_url: str = "https://personal.connectapi.garmin.com"
    garmin_timeout_seconds: float = 30
    garmin_poll_minutes: int = 30
    garmin_history_days: int = 30
    # Clave Fernet para secretos en BD; vacía = derivada de jwt_secret.
    encryption_key: str = ""
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
