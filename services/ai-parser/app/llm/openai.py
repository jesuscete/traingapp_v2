import httpx

from app.core.config import settings
from app.llm.base import JsonSchema
from app.llm.errors import LLMError, LLMTimeoutError
from app.llm.json_output import json_object


class OpenAIProvider:
    """Cualquier API compatible con /v1/chat/completions y `response_format` json_schema."""

    name = "openai"

    def __init__(
        self,
        *,
        api_key: str = settings.openai_api_key,
        base_url: str = settings.openai_base_url,
        model: str = settings.llm_model,
        timeout: float = settings.llm_timeout_seconds,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
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
        payload: dict[str, object] = {
            "model": self._model,
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "respuesta", "schema": schema},
            },
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(f"La API no respondió en {self._timeout}s") from exc
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMError(f"Fallo llamando a la API OpenAI-compatible: {exc}") from exc
        return json_object(content)
