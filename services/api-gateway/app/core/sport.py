"""Cliente de la redacción del análisis de deporte (ai-parser /analyze/sport)."""

from app.core.ai_parser_http import ai_parser_client


async def fetch_sport_narrative(sport_label: str, analysis: dict[str, object]) -> dict[str, object]:
    async with ai_parser_client() as client:
        response = await client.post(
            "/analyze/sport", json={"sportLabel": sport_label, "analysis": analysis}
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("ai-parser returned a non-object response")
        return data
