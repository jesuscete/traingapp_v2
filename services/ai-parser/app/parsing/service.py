import logging

from app.llm import factory
from app.parsing.llm import parse_with_llm
from app.parsing.stub import parse_text
from app.schemas.parse import ParseResponse

logger = logging.getLogger(__name__)


async def parse_workout(raw_text: str) -> ParseResponse:
    provider = factory.get_provider()
    if provider is None:
        return parse_text(raw_text)
    try:
        return await parse_with_llm(provider, raw_text)
    except Exception:
        logger.exception("LLM parse failed; falling back to deterministic stub")
        return parse_text(raw_text)
