import uuid

import httpx

from app.core.config import settings


async def fetch_draft(raw_text: str) -> dict[str, object]:
    request_id = str(uuid.uuid4())
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{settings.ai_parser_url.rstrip('/')}/parse",
            json={"requestId": request_id, "rawText": raw_text},
        )
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError("ai-parser returned a non-object response")
        return data
