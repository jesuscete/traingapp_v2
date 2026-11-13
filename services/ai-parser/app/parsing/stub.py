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

_HYROX = ("hyrox",)
_CROSSFIT = ("crossfit", "cross fit", "wod", "amrap", "emom", "for time", "tabata", "metcon")
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
        (_HYROX, "hyrox"),
        (_CROSSFIT, "crossfit"),
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


_WOD_FORMATS: tuple[tuple[str, str], ...] = (
    (r"\bamrap\b", "amrap"),
    (r"\be\d?mom\b", "emom"),
    (r"\btabata\b", "tabata"),
    (r"\bfor time\b|\brft\b|\brondas? por tiempo\b", "for_time"),
    (r"\bintervalos?\b", "intervals"),
)
_CAP = re.compile(r"(?:amrap|e\d?mom|time ?cap|cap)\D{0,4}(\d{1,3})\s*(?:min|')?")
_ROUNDS = re.compile(
    r"(\d{1,3})\s*(?:rondas?|rounds?|rds?)\s*(?:\+|y|mas|más)?\s*(\d{1,3})?"
)
_CLOCK = re.compile(r"\b(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\b")
_CATEGORY = (
    ("pro", "mujer", "pro_women"),
    ("pro", "", "pro_men"),
    ("open", "mujer", "open_women"),
    ("dobles", "", "doubles"),
    ("doubles", "", "doubles"),
    ("relevo", "", "relay"),
)


def _wod_metrics(text: str, discipline: str) -> dict[str, object] | None:
    """WOD sin LLM: formato, time cap, resultado, Rx/Scaled y categoría HYROX."""
    if discipline not in ("crossfit", "hyrox"):
        return None
    lowered = text.lower()
    wod: dict[str, object] = {"kind": "wod"}
    fmt = next((code for pattern, code in _WOD_FORMATS if re.search(pattern, lowered)), None)
    if discipline == "hyrox" and fmt is None:
        race = any(w in lowered for w in ("carrera", "competi", "race"))
        fmt = "hyrox_race" if race else "hyrox_sim"
    wod["format"] = fmt or "other"
    if (cap := _CAP.search(lowered)) is not None:
        wod["timeCapMinutes"] = int(cap.group(1))
    if wod["format"] == "amrap" and (rounds := _ROUNDS.search(lowered)) is not None:
        wod["rounds"] = int(rounds.group(1))
        if rounds.group(2):
            wod["extraReps"] = int(rounds.group(2))
    if (clock := _CLOCK.search(lowered)) is not None:
        hours, minutes, seconds = (int(g) if g else 0 for g in clock.groups())
        wod["timeSeconds"] = hours * 3600 + minutes * 60 + seconds
    if "scaled" in lowered or "escalad" in lowered:
        wod["rx"] = False
    if discipline == "hyrox":
        for word, extra, code in _CATEGORY:
            if word in lowered and extra in lowered:
                wod["hyroxCategory"] = code
                break
        else:
            if "open" in lowered:
                wod["hyroxCategory"] = "open_men"
    return wod


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
    discipline = _extract_discipline(text, bool(exercises))
    metrics = _wod_metrics(text, discipline)
    if metrics is not None:
        exercises = []  # en un WOD las cifras son reps por ronda, no series de gimnasio
        if duration is None and isinstance(metrics.get("timeCapMinutes"), int):
            duration = int(metrics["timeCapMinutes"])  # type: ignore[call-overload]
    return ParseResponse(
        rawText=text,
        discipline=discipline,
        performedAt=datetime.now(UTC).isoformat(),
        durationMinutes=duration,
        exercises=exercises,
        suggestedRpe=_suggested_rpe(exercises, duration),
        confidence=confidence,
        unresolved=[],
        metrics=metrics,
    )
