import re
from datetime import UTC, datetime

from app.schemas.parse import Discipline, ExerciseDraft, ParseResponse

_SETS_REPS_WEIGHT = re.compile(
    r"(\d+)\s*[xX×]\s*(\d+)\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s*(?:kg|kilos?)"
)
_HOURS = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:h|hora|horas)")
_MINUTES = re.compile(r"(\d+)\s*(?:min(?:uto)?s?|m\b)")

_BOXING = ("boxeo", "boxing")
_RUNNING = ("running", "correr", "carrera", "trote")
_CYCLING = ("ciclismo", "cycling", "bici")


def _extract_duration(text: str) -> int | None:
    hours = 0.0
    hours_match = _HOURS.search(text)
    if hours_match is not None:
        hours = float(hours_match.group(1).replace(",", "."))
    minutes = 0
    minutes_match = _MINUTES.search(text)
    if minutes_match is not None:
        minutes = int(minutes_match.group(1))
    total = round(hours * 60) + minutes
    return total if total > 0 else None


def _extract_exercises(text: str) -> list[ExerciseDraft]:
    exercises: list[ExerciseDraft] = []
    for match in _SETS_REPS_WEIGHT.finditer(text):
        exercises.append(
            ExerciseDraft(
                name=match.group(3).strip(),
                sets=int(match.group(1)),
                reps=int(match.group(2)),
                weight_kg=float(match.group(4).replace(",", ".")),
            )
        )
    return exercises


def _extract_discipline(text: str, has_exercises: bool) -> Discipline:
    lowered = text.lower()
    if any(kw in lowered for kw in _BOXING):
        return "boxing"
    if any(kw in lowered for kw in _RUNNING):
        return "running"
    if any(kw in lowered for kw in _CYCLING):
        return "cycling"
    if has_exercises:
        return "gym"
    return "other"


def parse_text(raw_text: str) -> ParseResponse:
    text = raw_text.strip()
    exercises = _extract_exercises(text)
    duration = _extract_duration(text)
    confidence = 0.9 if exercises else (0.7 if duration else 0.5)
    return ParseResponse(
        rawText=text,
        discipline=_extract_discipline(text, bool(exercises)),
        performedAt=datetime.now(UTC),
        durationMinutes=duration,
        exercises=exercises,
        confidence=confidence,
        unresolved=[],
    )
