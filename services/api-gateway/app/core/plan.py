"""Cliente HTTP del generador de planes (ai-parser).

Mismo patron que `app.core.parser.fetch_draft` y `app.core.review`: punto
unico desacoplado hacia el proveedor de IA.
"""

from app.core.ai_parser_http import ai_parser_client


async def fetch_plan_splits(
    sports: list[dict[str, object]], gym_days: int
) -> list[dict[str, object]]:
    async with ai_parser_client() as client:
        response = await client.post(
            "/plan/splits",
            json={
                "sports": [
                    {
                        "name": sport.get("name", ""),
                        "days": sport.get("days", []),
                        "durationMin": sport.get("durationMin"),
                    }
                    for sport in sports
                ],
                "gymDays": gym_days,
            },
        )
        response.raise_for_status()
        data = response.json()
        options = data.get("options") if isinstance(data, dict) else None
        return options if isinstance(options, list) else []


async def fetch_plan_generate(
    sports: list[dict[str, object]],
    gym_days: int,
    split_id: str | None,
    goal: str,
    catalog: list[str],
    system_prompt: str | None = None,
) -> dict[str, object]:
    async with ai_parser_client() as client:
        response = await client.post(
            "/plan/generate",
            json={
                "sports": [
                    {
                        "name": sport.get("name", ""),
                        "days": sport.get("days", []),
                        "durationMin": sport.get("durationMin"),
                    }
                    for sport in sports
                ],
                "gymDays": gym_days,
                "splitId": split_id,
                "goal": goal,
                "catalog": catalog,
                "systemPrompt": system_prompt,
            },
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("ai-parser returned a non-object plan response")
        return data
