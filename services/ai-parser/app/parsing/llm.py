import json
import logging
import re
from datetime import UTC, datetime

from app.llm.base import LLMProvider
from app.parsing.prompt import build_system_prompt
from app.schemas.parse import DISCIPLINES, ExerciseDraft, ParseResponse

logger = logging.getLogger(__name__)

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


async def parse_with_llm(provider: LLMProvider, raw_text: str) -> ParseResponse:
    content = await provider.complete(build_system_prompt(), raw_text)
    match = _JSON_OBJECT.search(content)
    if match is None:
        raise ValueError("LLM response contained no JSON object")
    data = json.loads(match.group(0))
    return _response_from(data, raw_text)


def _response_from(data: dict[str, object], raw_text: str) -> ParseResponse:
    discipline = data.get("discipline")
    if discipline not in DISCIPLINES:
        discipline = "other"
    exercises: list[ExerciseDraft] = []
    exercises_raw = data.get("exercises")
    if isinstance(exercises_raw, list):
        for raw in exercises_raw:
            if not isinstance(raw, dict):
                continue
            item: dict[str, object] = raw
            name = item.get("name")
            exercises.append(
                ExerciseDraft(
                    name=str(name).strip() if name is not None else "",
                    sets=_optional_int(item.get("sets")),
                    reps=_optional_int(item.get("reps")),
                    per_set_reps=_optional_int_list(
                        item.get("perSetReps") or item.get("per_set_reps")
                    ),
                    weight_kg=_optional_float(
                        item.get("weightKg") or item.get("weight_kg")
                    ),
                )
            )
    unresolved_raw = data.get("unresolved")
    unresolved = (
        [str(u) for u in unresolved_raw] if isinstance(unresolved_raw, list) else []
    )
    return ParseResponse(
        rawText=raw_text,
        discipline=discipline,
        performedAt=_parse_datetime(data.get("performedAt")).isoformat(),
        durationMinutes=_optional_int(data.get("durationMinutes")),
        exercises=exercises,
        suggestedRpe=_optional_float(data.get("suggestedRpe")),
        confidence=_optional_float(data.get("confidence"), default=0.7),
        unresolved=unresolved,
    )


def _parse_datetime(value: object) -> datetime:
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed
        except ValueError:
            logger.warning("Invalid performedAt from LLM: %s", value)
    return datetime.now(UTC)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _optional_int_list(value: object) -> list[int] | None:
    if not isinstance(value, list):
        return None
    result: list[int] = []
    for part in value:
        try:
            result.append(int(str(part)))
        except (TypeError, ValueError):
            continue
    return result or None


def _optional_float(value: object, default: float | None = None) -> float | None:
    if value is None:
        return default
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return default
