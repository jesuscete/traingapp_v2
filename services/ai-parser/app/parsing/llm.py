import logging
from datetime import UTC, datetime
from typing import Literal

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


CombatType = Literal["saco", "sparring", "manoplas", "comba", "sombra", "tecnica", "fisico"]
COMBAT_DISCIPLINES = frozenset({"boxing", "martial_arts"})
ENDURANCE_DISCIPLINES = frozenset({"running", "cycling", "swimming", "ski_snowboard"})
WOD_DISCIPLINES = frozenset({"crossfit", "hyrox"})
WodFormat = Literal[
    "for_time", "amrap", "emom", "tabata", "intervals", "strength", "hyrox_sim", "hyrox_race",
    "other",
]
HyroxCategory = Literal["open_men", "open_women", "pro_men", "pro_women", "doubles", "relay"]


class LlmCombatBlock(BaseModel):
    type: CombatType
    rounds: int | None = Field(default=None, ge=1, le=50)
    roundSeconds: int | None = Field(default=None, ge=10, le=600)
    minutes: float | None = Field(default=None, gt=0, le=300)


class LlmWodMovement(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    reps: int | None = Field(default=None, ge=1, le=10_000)
    weightKg: float | None = Field(default=None, gt=0, le=500)
    distanceM: float | None = Field(default=None, gt=0, le=100_000)
    calories: int | None = Field(default=None, ge=1, le=5_000)


class LlmWod(BaseModel):
    format: WodFormat = "other"
    name: str | None = Field(default=None, max_length=80)
    scheme: str | None = Field(default=None, max_length=60)
    timeCapMinutes: float | None = Field(default=None, gt=0, le=360)
    timeSeconds: int | None = Field(default=None, ge=1, le=6 * 3600)
    rounds: int | None = Field(default=None, ge=0, le=1_000)
    extraReps: int | None = Field(default=None, ge=0, le=10_000)
    totalReps: int | None = Field(default=None, ge=0, le=100_000)
    loadKg: float | None = Field(default=None, gt=0, le=500)
    rx: bool | None = None
    hyroxCategory: HyroxCategory | None = None
    movements: list[LlmWodMovement] = Field(default_factory=list, max_length=30)


class LlmWorkoutDraft(BaseModel):
    """Forma exacta que debe devolver el modelo (se pasa como JSON Schema)."""

    discipline: str
    performedAt: str | None = None
    durationMinutes: int | None = Field(default=None, ge=0)
    suggestedRpe: float | None = Field(default=None, ge=1, le=10)
    exercises: list[LlmExercise] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0, le=1)
    unresolved: list[str] = Field(default_factory=list)
    combatBlocks: list[LlmCombatBlock] = Field(default_factory=list)
    distanceMeters: float | None = Field(default=None, gt=0)
    avgHeartRate: int | None = Field(default=None, ge=30, le=230)
    elevationGainM: float | None = Field(default=None, ge=0)
    wod: LlmWod | None = None


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
        metrics=_metrics(draft, discipline),
        source="llm",
    )


def _metrics(draft: LlmWorkoutDraft, discipline: str) -> dict[str, object] | None:
    """Métricas por deporte con la forma que valida el api-gateway (`kind` + campos)."""
    if discipline in COMBAT_DISCIPLINES:
        blocks = [
            b.model_dump(exclude_none=True)
            for b in draft.combatBlocks
            if b.rounds is not None or b.minutes is not None
        ]
        return {"kind": "combat", "blocks": blocks} if blocks else None
    if discipline in ENDURANCE_DISCIPLINES:
        endurance = {
            "distanceMeters": draft.distanceMeters,
            "avgHeartRate": draft.avgHeartRate,
            "elevationGainM": draft.elevationGainM,
        }
        present = {k: v for k, v in endurance.items() if v is not None}
        return {"kind": "endurance", **present} if present else None
    if discipline in WOD_DISCIPLINES and draft.wod is not None:
        wod = draft.wod.model_dump(exclude_none=True)
        if not wod.get("movements"):
            wod.pop("movements", None)
        return {"kind": "wod", **wod}
    return None


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
