import httpx

from app.core.config import settings
from app.llm.base import JsonSchema
from app.llm.errors import LLMError, LLMTimeoutError
from app.llm.json_output import json_object


class OllamaProvider:
    name = "ollama"

    def __init__(
        self,
        *,
        url: str = settings.ollama_url,
        model: str = settings.llm_model,
        timeout: float = settings.llm_timeout_seconds,
    ) -> None:
        self._url = url.rstrip("/")
        self._model = model
        self._timeout = timeout

    async def complete_json(
        self,
        system: str,
        user: str,
        *,
        schema: JsonSchema,
        max_tokens: int | None = None,
    ) -> dict[str, object]:
        options: dict[str, object] = {"num_ctx": settings.llm_context_length}
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._url}/api/chat",
                    json={
                        "model": self._model,
                        "stream": False,
                        "format": schema,  # salida estructurada nativa de Ollama
                        "think": False,
                        "options": options,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                    },
                )
                response.raise_for_status()
                content = response.json()["message"]["content"]
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"Ollama no respondió en {self._timeout}s") from exc
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise LLMError(f"Fallo llamando a Ollama: {exc}") from exc
        return json_object(content)

