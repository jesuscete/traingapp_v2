import logging

from app.llm import factory
from app.llm.errors import LLMError
from app.parsing.llm import parse_with_llm
from app.parsing.stub import parse_structured, parse_text
from app.schemas.parse import ParseResponse

logger = logging.getLogger(__name__)


def _fallback(raw_text: str) -> ParseResponse:
    return parse_text(raw_text).model_copy(update={"source": "fallback"})


async def parse_workout(raw_text: str) -> ParseResponse:
    structured = parse_structured(raw_text)
    if structured is not None:
        return structured  # lista clara de ejercicios: sin IA (M10)
    provider = factory.get_provider()
    if provider is None:
        return _fallback(raw_text)
    try:
        return await parse_with_llm(provider, raw_text)
    except LLMError:
        logger.exception("LLM parse failed (%s); using deterministic stub", provider.name)
        return _fallback(raw_text)
