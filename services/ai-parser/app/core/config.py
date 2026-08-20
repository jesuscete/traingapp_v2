from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

    app_name: str = "ai-parser"
    app_env: str = "development"
    redis_url: str = "redis://localhost:6379/0"
    internal_api_url: str = "http://localhost:8000"
    internal_token: str = "internal-dev-token"

    # Adaptador LLM plug-and-play (ADR-012): ollama | openai | stub
    llm_provider: str = "stub"
    llm_model: str = "qwen2.5:3b"
    ollama_url: str = "http://localhost:11434"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    llm_timeout_seconds: int = 30
    # Contexto maximo para el LLM local (limita la caché KV de memoria).
    llm_context_length: int = 8192
    # Tope de tokens de salida para la evaluación de rutinas (reduce la latencia
    # de generación en CPU; la respuesta tiene pocos items).
    llm_review_max_tokens: int = 800


settings = Settings()
