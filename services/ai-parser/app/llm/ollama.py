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

    async def complete(self, system: str, user: str) -> str:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._url}/api/chat",
                json={
                    "model": self._model,
                    "stream": False,
                    "format": "json",
                    "think": False,
                    "options": {"num_ctx": settings.llm_context_length},
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            return str(data["message"]["content"])
