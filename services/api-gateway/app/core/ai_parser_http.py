"""Cliente HTTP único hacia ai-parser: URL base, token interno y timeout común."""

import httpx

from app.core.config import settings


def ai_parser_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.ai_parser_url.rstrip("/"),
        timeout=settings.ai_parser_timeout_seconds,
        headers={"X-Internal-Token": settings.internal_token},
    )
