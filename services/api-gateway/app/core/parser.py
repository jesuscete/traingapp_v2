import uuid

from app.core.ai_parser_http import ai_parser_client


async def fetch_draft(raw_text: str) -> dict[str, object]:
    request_id = str(uuid.uuid4())
    async with ai_parser_client() as client:
        response = await client.post(
            "/parse",
            json={"requestId": request_id, "rawText": raw_text},
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("ai-parser returned a non-object response")
        return data
