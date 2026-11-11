from app.core.config import settings
from app.llm.base import LLMProvider
from app.llm.claude_cli import ClaudeCliProvider
from app.llm.ollama import OllamaProvider
from app.llm.openai import OpenAIProvider


def get_provider() -> LLMProvider | None:
    """Proveedor configurado, o None para usar solo los stubs deterministas."""
    match settings.llm_provider:
        case "claude_cli":
            return ClaudeCliProvider()
        case "ollama":
            return OllamaProvider()
        case "openai":
            return OpenAIProvider()
        case "stub":
            return None
