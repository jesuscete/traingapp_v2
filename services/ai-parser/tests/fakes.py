from app.llm.base import JsonSchema
from app.llm.json_output import json_object


class TextFakeProvider:
    """Adaptador de tests: los fakes devuelven texto JSON desde `complete`."""

    name = "fake"
    last_max_tokens: int | None = None
    calls: int = 0

    async def complete(self, system: str, user: str) -> str:
        raise NotImplementedError

    async def complete_json(
        self,
        system: str,
        user: str,
        *,
        schema: JsonSchema,
        max_tokens: int | None = None,
    ) -> dict[str, object]:
        self.last_max_tokens = max_tokens
        self.calls += 1
        return json_object(await self.complete(system, user))
