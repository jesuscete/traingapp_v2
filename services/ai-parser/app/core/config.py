from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

    app_name: str = "ai-parser"
    app_env: str = "development"
    redis_url: str = "redis://localhost:6379/0"
    internal_api_url: str = "http://localhost:8000"
    internal_token: str = "internal-dev-token"


settings = Settings()
