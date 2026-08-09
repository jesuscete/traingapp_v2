from app.core.config import settings
from app.llm.base import LLMProvider
from app.llm.ollama import OllamaProvider
from app.llm.openai import OpenAIProvider


def get_provider() -> LLMProvider | None:
    if settings.llm_provider == "ollama":
        return OllamaProvider()
    if settings.llm_provider == "openai":
        return OpenAIProvider()
    return None
