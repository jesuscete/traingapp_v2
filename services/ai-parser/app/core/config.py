from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_INTERNAL_TOKEN = "internal-dev-token"
MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

    app_name: str = "ai-parser"
    app_env: str = "development"
    redis_url: str = "redis://localhost:6379/0"
    internal_api_url: str = "http://localhost:8000"
    internal_token: str = DEV_INTERNAL_TOKEN

    # Proveedor LLM (ADR-002): claude_cli | ollama | openai | stub
    llm_provider: Literal["claude_cli", "ollama", "openai", "stub"] = "stub"
    llm_model: str = "qwen2.5:3b"
    # Claude vía CLI local (suscripción de Claude Code): alias o id de modelo.
    claude_cli_path: str = "claude"
    claude_model: str = "sonnet"
    # M10 · modelo por tarea: las tareas cortas y de salida cerrada usan el modelo rápido.
    # Añadir "agent" cuando se haya comprobado que la calidad del chat no baja.
    claude_model_fast: str = "haiku"
    llm_fast_tasks: str = ""  # medido 2026-11-13: Haiku por CLI no fue más rápido (9 s vs 6 s)
    ollama_url: str = "http://localhost:11434"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_timeout_seconds: int = 90
    # Contexto maximo para el LLM local (limita la caché KV de memoria).
    llm_context_length: int = 8192
    # Tope de tokens de salida para la evaluación de rutinas (reduce la latencia
    # de generación en CPU; la respuesta tiene pocos items).
    llm_review_max_tokens: int = 800

    @model_validator(mode="after")
    def _reject_dev_secrets_in_production(self) -> Self:
        if self.app_env == "production" and (
            self.internal_token == DEV_INTERNAL_TOKEN
            or len(self.internal_token) < MIN_SECRET_LENGTH
        ):
            raise ValueError(
                "Secretos inseguros en producción: APP_INTERNAL_TOKEN "
                f"(default o < {MIN_SECRET_LENGTH} caracteres)"
            )
        return self


settings = Settings()
