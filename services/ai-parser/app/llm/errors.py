class LLMError(Exception):
    """Fallo al obtener una respuesta válida del proveedor LLM."""


class LLMTimeoutError(LLMError):
    """El proveedor no respondió dentro del tiempo límite."""


class LLMOutputError(LLMError):
    """La respuesta no cumple el esquema esperado ni tras el reintento de reparación."""
