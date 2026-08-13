import json
import logging
import re

from app.llm import factory
from app.review.prompt import SYSTEM_PROMPT, build_user_message
from app.review.stub import stub_review
from app.schemas.review import RoutineReviewRequest, RoutineReviewResponse, Solapamiento

logger = logging.getLogger(__name__)

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


async def review_routine(body: RoutineReviewRequest) -> RoutineReviewResponse:
    provider = factory.get_provider()
    if provider is None:
        return stub_review(body.days)
    try:
        content = await provider.complete(
            SYSTEM_PROMPT, build_user_message(_payload(body))
        )
        return _response_from(content)
    except Exception:
        logger.exception("LLM routine review failed; falling back to deterministic stub")
        return stub_review(body.days)


def _payload(body: RoutineReviewRequest) -> dict[str, object]:
    return {"routineName": body.routineName, "days": body.days}


def _response_from(content: str) -> RoutineReviewResponse:
    match = _JSON_OBJECT.search(content)
    if match is None:
        raise ValueError("LLM response contained no JSON object")
    data = json.loads(match.group(0))
    puntos = _string_list(data.get("puntosFuerte") or data.get("puntos_fuerte"))
    sugerencias = _string_list(data.get("sugerencias"))
    solapamientos: list[Solapamiento] = []
    raw = data.get("solapamientos")
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            solapamientos.append(
                Solapamiento(
                    descripcion=str(item.get("descripcion") or ""),
                    grupos=_string_list(item.get("grupos")),
                    dias=_string_list(item.get("dias")),
                )
            )
    return RoutineReviewResponse(
        puntosFuerte=puntos,
        solapamientos=solapamientos,
        sugerencias=sugerencias,
    )


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for part in value:
        if isinstance(part, str) and part.strip():
            result.append(part.strip())
    return result