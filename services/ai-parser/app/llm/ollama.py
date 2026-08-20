import httpx

from app.core.config import settings


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

    async def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int | None = None,
    ) -> str:
        options: dict[str, object] = {"num_ctx": settings.llm_context_length}
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._url}/api/chat",
                json={
                    "model": self._model,
                    "stream": False,
                    "format": "json",
                    "think": False,
                    "options": options,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            return str(data["message"]["content"])
