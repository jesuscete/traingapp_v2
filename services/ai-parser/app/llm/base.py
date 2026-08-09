from typing import Protocol


class LLMProvider(Protocol):
    name: str

    async def complete(self, system: str, user: str) -> str: ...
