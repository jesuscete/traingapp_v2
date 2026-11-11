import json

from app.llm.errors import LLMError


def json_object(content: object) -> dict[str, object]:
    """Decodifica la respuesta del modelo exigiendo un objeto JSON."""
    try:
        data = json.loads(str(content))
    except json.JSONDecodeError as exc:
        raise LLMError("La respuesta del modelo no es JSON") from exc
    if not isinstance(data, dict):
        raise LLMError("La respuesta del modelo no es un objeto JSON")
    return data
