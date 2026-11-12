"""Cliente del parseo de comidas en texto libre (ai-parser /parse/meal)."""

from app.core.ai_parser_http import ai_parser_client


async def fetch_meal_parse(text: str) -> dict[str, object]:
    async with ai_parser_client() as client:
        response = await client.post("/parse/meal", json={"text": text})
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("ai-parser returned a non-object response")
        return data
