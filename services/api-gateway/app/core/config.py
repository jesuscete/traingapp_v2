from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

    app_name: str = "api-gateway"
    app_env: str = "development"
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = (
        "postgresql+asyncpg://traingapp:traingapp@localhost:5432/traingapp"
    )
    jwt_secret: str = "dev-secret-change-me-0123456789abcdef"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    internal_token: str = "internal-dev-token"
    ai_parser_url: str = "http://localhost:8100"
    chat_draft_ttl_seconds: int = 1800
    live_session_ttl_seconds: int = 14400
    plan_session_ttl_seconds: int = 3600


settings = Settings()
