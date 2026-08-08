import httpx

from app.core.config import settings


class OpenAIProvider:
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

    async def complete(self, system: str, user: str) -> str:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "temperature": 0,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            response.raise_for_status()
            data = response.json()
            return str(data["choices"][0]["message"]["content"])
