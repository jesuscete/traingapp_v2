from typing import Protocol

JsonSchema = dict[str, object]


class LLMProvider(Protocol):
    name: str

    async def complete_json(
        self,
        system: str,
        user: str,
        *,
        schema: JsonSchema,
        max_tokens: int | None = None,
    ) -> dict[str, object]:
        """Devuelve un objeto JSON que el proveedor intenta ajustar a `schema`.

        Lanza `LLMError` (o subclases) ante cualquier fallo de transporte o formato.
        """
        ...
