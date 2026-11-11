import logging
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.llm.base import LLMProvider
from app.llm.structured import generate, user_data, with_user_data_rule
from app.parsing.prompt import build_system_prompt
from app.schemas.parse import DISCIPLINES, ExerciseDraft, ParseResponse

logger = logging.getLogger(__name__)

DEFAULT_CONFIDENCE = 0.7


class LlmExercise(BaseModel):
    name: str = Field(min_length=1)
    sets: int | None = Field(default=None, ge=1)
    reps: int | None = Field(default=None, ge=1)
    perSetReps: list[int] | None = None
    weightKg: float | None = Field(default=None, ge=0)


class LlmWorkoutDraft(BaseModel):
    """Forma exacta que debe devolver el modelo (se pasa como JSON Schema)."""

    discipline: str
    performedAt: str | None = None
    durationMinutes: int | None = Field(default=None, ge=0)
    suggestedRpe: float | None = Field(default=None, ge=1, le=10)
    exercises: list[LlmExercise] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    unresolved: list[str] = Field(default_factory=list)


async def parse_with_llm(provider: LLMProvider, raw_text: str) -> ParseResponse:
    draft = await generate(
        provider,
        with_user_data_rule(build_system_prompt()),
        user_data(raw_text),
        LlmWorkoutDraft,
    )
    return _response_from(draft, raw_text)


def _response_from(draft: LlmWorkoutDraft, raw_text: str) -> ParseResponse:
    discipline = draft.discipline if draft.discipline in DISCIPLINES else "other"
    return ParseResponse(
        rawText=raw_text,
        discipline=discipline,
        performedAt=_parse_datetime(draft.performedAt).isoformat(),
        durationMinutes=draft.durationMinutes,
        exercises=[
            ExerciseDraft(
                name=ex.name.strip(),
                sets=ex.sets,
                reps=ex.reps,
                per_set_reps=_positive(ex.perSetReps),
                weight_kg=ex.weightKg,
            )
            for ex in draft.exercises
        ],
        suggestedRpe=draft.suggestedRpe,
        confidence=draft.confidence if draft.confidence is not None else DEFAULT_CONFIDENCE,
        unresolved=[u.strip() for u in draft.unresolved if u.strip()],
        source="llm",
    )


def _positive(values: list[int] | None) -> list[int] | None:
    kept = [v for v in values or [] if v > 0]
    return kept or None


def _parse_datetime(value: str | None) -> datetime:
    if value:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed
        except ValueError:
            logger.warning("Invalid performedAt from LLM: %s", value)
    return datetime.now(UTC)
