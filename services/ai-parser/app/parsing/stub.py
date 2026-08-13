import re
from datetime import UTC, datetime
from typing import cast

from app.schemas.parse import Discipline, ExerciseDraft, ParseResponse

_SERIES_SETS = re.compile(
    r"([^:\n]+?)\s*:\s*(\d+(?:\s*,\s*\d+)+)"
    r"(?:\s*[xX×]\s*(\d+(?:[.,]\d+)?)\s*(?:kg|kilos?)?"
    r"|\s*\(\s*(\d+(?:[.,]\d+)?)\s*kg\s*\))?"
)
_SETS_REPS_WEIGHT = re.compile(
    r"(\d+)\s*[xX×]\s*(\d+)\s+(.+?)\s+(\d+(?:[.,]\d+)?)\s*(?:kg|kilos?)"
)
_HOURS = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:h|hora|horas)")
_MINUTES = re.compile(r"(\d+)\s*(?:min(?:uto)?s?|m\b)")

_BOXING = ("boxeo", "boxing")
_MARTIAL_ARTS = ("artes marciales", "karate", "judo", "taekwondo", "mma")
_RUNNING = ("running", "correr", "carrera", "trote")
_CYCLING = ("ciclismo", "cycling", "bici")
_SWIMMING = ("natación", "natacion", "swimming", "nadar", "piscina")
_CLIMBING = ("escalada", "climbing", "boulder")
_CALISTHENICS = ("calistenia", "calisthenics", "bodyweight")
_FOOTBALL = ("fútbol", "futbol", "football")
_BASKETBALL = ("baloncesto", "basketball")
_VOLLEYBALL = ("voleibol", "volleyball", "vóley")
_CRICKET = ("cricket", "críquet")
_BASEBALL = ("béisbol", "beisbol", "baseball")
_HOCKEY = ("hockey",)
_RUGBY = ("rugby",)
_HANDBALL = ("balonmano", "handball")
_BADMINTON = ("bádminton", "badminton")
_TABLE_TENNIS = ("tenis de mesa", "pimpón", "pimon", "ping pong", "table tennis")
_TENNIS = ("tenis", "tennis")
_SKI = ("esquí", "esqui", "snowboard", "ski")
_GOLF = ("golf",)


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
    for match in _SERIES_SETS.finditer(text):
        per_set = [int(part.strip()) for part in match.group(2).split(",")]
        weight_str = match.group(3) or match.group(4)
        exercises.append(
            ExerciseDraft(
                name=match.group(1).strip(),
                sets=len(per_set),
                reps=round(sum(per_set) / len(per_set)),
                per_set_reps=per_set,
                weight_kg=(
                    float(weight_str.replace(",", ".")) if weight_str else None
                ),
            )
        )
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
    for keywords, code in (
        (_TABLE_TENNIS, "table_tennis"),
        (_TENNIS, "tennis"),
        (_BOXING, "boxing"),
        (_MARTIAL_ARTS, "martial_arts"),
        (_SWIMMING, "swimming"),
        (_SKI, "ski_snowboard"),
        (_BADMINTON, "badminton"),
        (_BASKETBALL, "basketball"),
        (_FOOTBALL, "football"),
        (_CYCLING, "cycling"),
        (_RUNNING, "running"),
        (_CLIMBING, "climbing"),
        (_CALISTHENICS, "calisthenics"),
        (_VOLLEYBALL, "volleyball"),
        (_CRICKET, "cricket"),
        (_BASEBALL, "baseball"),
        (_HOCKEY, "hockey"),
        (_RUGBY, "rugby"),
        (_HANDBALL, "handball"),
        (_GOLF, "golf"),
    ):
        if any(kw in lowered for kw in keywords):
            return cast(Discipline, code)
    if has_exercises:
        return "gym"
    return "other"


def _suggested_rpe(
    exercises: list[ExerciseDraft], duration: int | None
) -> float | None:
    if exercises:
        return 8.0
    if duration is not None:
        return 6.5
    return None


def parse_text(raw_text: str) -> ParseResponse:
    text = raw_text.strip()
    exercises = _extract_exercises(text)
    duration = _extract_duration(text)
    confidence = 0.9 if exercises else (0.7 if duration else 0.5)
    return ParseResponse(
        rawText=text,
        discipline=_extract_discipline(text, bool(exercises)),
        performedAt=datetime.now(UTC).isoformat(),
        durationMinutes=duration,
        exercises=exercises,
        suggestedRpe=_suggested_rpe(exercises, duration),
        confidence=confidence,
        unresolved=[],
    )
