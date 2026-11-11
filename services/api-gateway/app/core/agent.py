"""Cliente del paso del agente (ai-parser /agent/step)."""

from app.core.ai_parser_http import ai_parser_client


async def fetch_agent_step(payload: dict[str, object]) -> dict[str, object]:
    async with ai_parser_client() as client:
        response = await client.post("/agent/step", json=payload)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("ai-parser returned a non-object response")
        return data
