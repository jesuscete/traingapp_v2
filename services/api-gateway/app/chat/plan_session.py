"""Maquina de estados conversacional para crear un plan/rutina via chat.

El estado vive en Redis (key `plan:session:{user_id}`) igual que la sesion en
vivo: el backend orquesta el guion (UNA pregunta a la vez) y la IA solo
interviene al generar el plan final (ai-parser) y al elegir el split
automaticamente segun los dias de gimnasio declarados.

Flujo:
    trigger -> (confirm opcional si la intencion es ambigua) -> sports ->
    (por deporte) weekdays -> duration -> gym_purpose -> gym_days ->
    gym_split -> summary (resumen + confirmacion explicita) -> persist
    (create_routine).
"""

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.catalog import normalize_exercise_name
from app.chat.conversation import (
    is_end as _is_live_end,
)
from app.chat.conversation import (
    is_routine_start as _is_routine_start,
)
from app.chat.conversation import (
    is_start as _is_live_start,
)
from app.core.config import settings
from app.core.plan import fetch_plan_generate, fetch_plan_splits
from app.crud import routine as routine_crud
from app.crud.catalog import CatalogExercise, catalog_lookup
from app.models import Discipline, Routine
from app.schemas.plan import (
    PlanDayOut,
    PlanExerciseOut,
    PlanSetTargetOut,
    PlanSplitOut,
    PlanSummaryOut,
)
from app.schemas.routine import (
    RoutineDayIn,
    RoutineExerciseIn,
    RoutineIn,
    RoutineSetIn,
)

PLAN_KEY = "plan:session"

# Intencion clara de crear/recibir un plan: se arranca directamente con las
# preguntas (deporte -> dias -> duracion -> gimnasio -> resumen).
_STRONG_PLAN_PATTERNS: tuple[str, ...] = (
    r"\bcrear\b.*\b(rutina|plan)\b",
    r"\bcrea(rme)?\b.*\b(rutina|plan)\b",
    r"\b(hazme|hacer|arme|hacerte)\b.*\b(rutina|plan)\b",
    r"\b(armar|montar|generar|preparar|dise[nñ]ar)\w*\b.*\b(rutina|plan)\b",
    r"\brecom[i]?end\w*\b.*\b(rutina|plan)\b",
    r"\b(quiero|quisiera|me gustar[ií]a|me har[ií]a|necesito|necesitar[ií]a)\b.*\b(rutina|plan)\b",
    r"\bvoy a (crear|hacer|montar|armar)\b.*\b(rutina|plan)\b",
    r"\bempezar a\b.*\b(rutina|plan)\b",
)

# Indicios ambiguos de plan: no esta claro, se pregunta "¿Quieres que te
# recomiende un plan?" antes de arrancar las preguntas.
_MAYBE_PLAN_PATTERNS: tuple[str, ...] = (
    r"\b(recom[i]?end\w*|ay[uú]dame|ay[uú]date|sug[ie]r\w*|aconsej\w*)\b",
    r"\b(rutina|rutinas|plan|planes|entrenamiento)\b",
    r"\b(necesit\w*|empezar a entrenar|irme al gym|ir al gym|ponerme (en forma|fuerte)|"
    r"quiero entrenar)\b",
)

_NONE_PATTERN = re.compile(r"\b(no|ninguno|ningun|nada)\b", re.IGNORECASE)
_CONFIRM_PATTERN = re.compile(
    r"^\s*(?:s[ií]|s[ií][\s,¡!]*(?:claro|quiero|adelante|dale|por favor|me interesa|venga|"
    r"s[uú]per)|"
    r"claro|adelante|dale|vale|venga|perfecto|me interesa|ok|de acuerdo|confirmar|guardar|"
    r"gu[aá]rdala|gu[aá]rdalo)\s*[\.,!¡]?\s*$",
    re.IGNORECASE,
)
_CANCEL_PATTERN = re.compile(
    r"^\s*(?:no|nop|no gracias|no quiero|cancelar|descartar|quita|no lo guardes|"
    r"ni hablar|ni idea|para)\s*[\.,!¡]?\s*$",
    re.IGNORECASE,
)

_SPORTS_QUESTION = (
    "¡Genial! Vamos a crear tu plan semanal paso a paso. Primero: "
    "¿qué deporte(s) practicas? Dime cuál o cuáles (ej: «hago boxeo y salgo "
    "a correr»), o «no» si no practicas ninguno."
)
_CONFIRM_QUESTION = (
    "Claro, puedo ayudarte con eso. ¿Quieres que te recomiende un plan de "
    "entrenamiento personalizado?"
)
_CONFIRM_CANCELLED_MESSAGE = (
    "Vale, no hay problema. Si cambias de idea, aquí estoy. ¿Te ayudo con algo más?"
)
# Nombre de deporte legible para preguntar/resumir (el usuario escribe verbos).
_SPORT_DISPLAY: dict[str, str] = {
    "corro": "correr",
    "correr": "correr",
    "carrera": "correr",
    "trote": "correr",
    "bici": "bicicleta",
    "ciclismo": "bicicleta",
    "futbol": "fútbol",
    "baloncesto": "baloncesto",
    "balonmano": "balonmano",
    "voleibol": "voleibol",
    "voley": "voleibol",
    "beisbol": "béisbol",
    "esqui": "esquí",
    "natacion": "natación",
    "artes marciales": "artes marciales",
}


def _display_sport_name(raw: str) -> str:
    normalized = normalize_exercise_name(raw)
    return _SPORT_DISPLAY.get(normalized, raw.strip())


_SPLIT_QUESTION = (
    "¿Qué tipo de rutina de gimnasio prefieres?\n"
    "- fullbody (cuerpo completo)\n"
    "- empuje-tirón (push/pull)\n"
    "- torso-pierna\n"
    "- upper/lower\n"
    "- me da igual (yo elijo)"
)


def _gym_purpose_question(plan: "PlanSession") -> str:
    names = [sport.name for sport in plan.sports]
    if not names:
        return "¿Quieres ir al gimnasio? (sí para entrenar de forma general o no)"
    if len(names) == 1:
        return (
            f"¿Quieres ir al gimnasio para mejorar en {names[0]}, para entrenar "
            "de forma general, o no quieres ir al gimnasio?"
        )
    targets = ", ".join(f"mejorar en {name}" for name in names[:-1])
    targets = f"{targets} o {names[-1]}"
    return (
        f"¿Quieres ir al gimnasio para {targets}, para entrenar de forma "
        "general, o no quieres ir al gimnasio?"
    )


def _gym_days_question() -> str:
    return (
        "¿Cuántos días a la semana quieres ir al gimnasio? "
        "(responde con un número del 1 al 7)"
    )

_WEEKDAY_NAMES: dict[int, str] = {
    1: "Lunes",
    2: "Martes",
    3: "Miércoles",
    4: "Jueves",
    5: "Viernes",
    6: "Sábado",
    7: "Domingo",
}

# Alias de deporte -> normalized_name de la tabla `discipline`.
_DISCIPLINE_ALIASES: dict[str, str] = {
    "boxeo": "boxing",
    "natacion": "swimming",
    "correr": "running",
    "corro": "running",
    "carrera": "running",
    "trote": "running",
    "jogging": "running",
    "bici": "cycling",
    "ciclismo": "cycling",
    "futbol": "football",
    "baloncesto": "basketball",
    "balonmano": "handball",
    "voleibol": "volleyball",
    "voley": "volleyball",
    "beisbol": "baseball",
    "cricket": "cricket",
    "hockey": "hockey",
    "rugby": "rugby",
    "tenis": "tennis",
    "badminton": "badminton",
    "ping pong": "table_tennis",
    "pimon": "table_tennis",
    "escalada": "climbing",
    "calistenia": "calisthenics",
    "esqui": "ski_snowboard",
    "snowboard": "ski_snowboard",
    "golf": "golf",
    "karate": "martial_arts",
    "artes marciales": "martial_arts",
    "mma": "martial_arts",
}


def plan_intent(text: str) -> str:
    """Clasifica el mensaje respecto a la intencion de crear un plan.

    Devuelve "clear" (arrancar preguntas ya), "maybe" (pedir confirmacion
    primero) o "none" (no tiene que ver con un plan).
    """
    if _is_live_start(text) or _is_routine_start(text) or _is_live_end(text):
        return "none"
    normalized = normalize_exercise_name(text)
    if any(
        re.search(pattern, normalized) for pattern in _STRONG_PLAN_PATTERNS
    ):
        return "clear"
    if any(
        re.search(pattern, normalized) for pattern in _MAYBE_PLAN_PATTERNS
    ):
        return "maybe"
    return "none"


def is_plan_start(text: str) -> bool:
    return plan_intent(text) == "clear"


def is_confirm(text: str) -> bool:
    return _CONFIRM_PATTERN.search(text.strip()) is not None


def is_cancel(text: str) -> bool:
    return _CANCEL_PATTERN.search(text.strip()) is not None


_SPORT_VERB_PATTERN = re.compile(
    r"^\s*(?:hago|practico|salgo a|juego a|entreno|suelo hacer|hacer|voy a hacer)\s+",
    re.IGNORECASE,
)


def parse_sports_answer(text: str) -> list[str] | None:
    """'hago boxeo y salgo a correr' -> ['boxeo', 'correr']; 'no' -> []; ilegible -> None."""
    if _NONE_PATTERN.search(text):
        return []
    parts = re.split(r"\s*(?:,|&|;|\by\b|\be\b|\band\b)\s*", text, flags=re.IGNORECASE)
    names: list[str] = []
    for part in parts:
        cleaned = _SPORT_VERB_PATTERN.sub("", part.strip()).strip(".,")
        if cleaned:
            names.append(_display_sport_name(cleaned))
    return names[:5] if names else None


_WORD_DAYS: dict[str, int] = {
    "uno": 1,
    "una": 1,
    "dos": 2,
    "tres": 3,
    "cuatro": 4,
    "cinco": 5,
    "seis": 6,
    "siete": 7,
}


def parse_day_count(text: str) -> int | None:
    """'2', 'dos', 'tres días' -> 1..7; ilegible -> None."""
    lowered = text.lower().strip()
    for word, value in _WORD_DAYS.items():
        if re.search(rf"\b{word}\b", lowered):
            return value
    match = re.search(r"(?<![\d.])([1-7])(?![\d.])", lowered)
    return int(match.group(1)) if match is not None else None


def spread_days(count: int) -> list[int]:
    """Distribuye `count` días de entrenamiento a lo largo de la semana (1=lu..7=do)."""
    if count <= 0:
        return []
    if count == 1:
        return [3]
    span = 6
    return sorted(1 + (i * span // (count - 1)) for i in range(count))


_HOURS_PATTERN = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:h|hora|horas)")
_MINUTES_PATTERN = re.compile(r"(\d+)\s*(?:min(?:utos?)?|m\b)")
_BARE_NUMBER_PATTERN = re.compile(r"\b(\d{1,3})\b")


def parse_duration_answer(text: str) -> int | None:
    lowered = text.lower()
    minutes = 0
    hours_match = _HOURS_PATTERN.search(lowered)
    if hours_match is not None:
        minutes += round(float(hours_match.group(1).replace(",", ".")) * 60)
    minutes_match = _MINUTES_PATTERN.search(lowered)
    if minutes_match is not None:
        minutes += int(minutes_match.group(1))
    if minutes > 0:
        return minutes
    bare = _BARE_NUMBER_PATTERN.search(lowered)
    if bare is not None:
        value = int(bare.group(1))
        if 1 <= value <= 720:
            return value
    return None


_DAY_NUMBER_PATTERN = re.compile(r"(?<![\d.])([1-7])(?![\d.])")


def parse_gym_days_answer(text: str) -> int | None:
    if _NONE_PATTERN.search(text):
        return 0
    match = _DAY_NUMBER_PATTERN.search(text)
    if match is not None:
        value = int(match.group(1))
        if value <= 7:
            return value
    return None


_WEEKDAY_ALIASES: dict[str, int] = {
    "lunes": 1,
    "martes": 2,
    "miercoles": 3,
    "jueves": 4,
    "viernes": 5,
    "sabado": 6,
    "domingo": 7,
    "lun": 1,
    "mar": 2,
    "mie": 3,
    "jue": 4,
    "vie": 5,
    "sab": 6,
    "dom": 7,
}
_WEEKDAY_ALIAS_PATTERN = re.compile(
    r"(lunes|martes|miercoles|jueves|viernes|sabado|domingo|lun|mar|mie|jue|vie|sab|dom)",
    re.IGNORECASE,
)


def parse_weekdays_answer(text: str) -> list[int] | None:
    """'lunes y jueves', '1 y 4', 'entre semana' -> dias 1..7; ilegible -> None."""
    lowered = normalize_exercise_name(text)
    if re.search(r"\b(entre semana|todos los dias|toda la semana|semana entera)\b", lowered):
        return [1, 2, 3, 4, 5]
    if re.search(r"\b(fin de semana|finde|fines de semana)\b", lowered):
        return [6, 7]
    days: list[int] = []
    for match in _WEEKDAY_ALIAS_PATTERN.finditer(lowered):
        days.append(_WEEKDAY_ALIASES[match.group(1).lower()])
    for match in _DAY_NUMBER_PATTERN.finditer(lowered):
        days.append(int(match.group(1)))
    return sorted(set(days)) if days else None


def parse_gym_purpose_answer(text: str, sports: list["SportAnswer"]) -> str | None:
    """Devuelve el nombre de un deporte, 'general', 'none' (no gimnasio) o None."""
    if _NONE_PATTERN.search(text):
        return "none"
    lowered = normalize_exercise_name(text)
    if re.search(r"\b(general|gimnasio|gym|pesas|fuerza|musculo|normal)\b", lowered):
        return "general"
    for sport in sports:
        if sport.name and normalize_exercise_name(sport.name) in lowered:
            return sport.name
    return None


def parse_split_choice(text: str) -> str | None:
    """fullbody | push_pull | torso_pierna | upper_lower | any | None (ilegible)."""
    lowered = normalize_exercise_name(text)
    if re.search(
        r"\b(da igual|me da igual|indiferente|cualquiera|tu decides|"
        r"tu eliges|te lo dejo|recomiendame)\b",
        lowered,
    ):
        return "any"
    if re.search(r"\b(fullbody|full body|cuerpo completo)\b", lowered):
        return "fullbody"
    if re.search(r"\b(empuje|push|tiron|push.?pull)\b", lowered):
        return "push_pull"
    if re.search(r"\b(torso|torso.?pierna)\b", lowered):
        return "torso_pierna"
    if re.search(r"\b(upper|lower|weider|weither|superior.?inferior)\b", lowered):
        return "upper_lower"
    return None


_SPLIT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "fullbody": ("fullbody", "full body", "cuerpo completo"),
    "push_pull": ("push", "pull", "empuje", "tiron"),
    "torso_pierna": ("torso", "torso pierna"),
    "upper_lower": ("upper", "lower", "weider", "weither"),
}


def _pick_split(options: list[dict[str, object]], choice: str | None) -> str | None:
    if not options:
        return None
    first_id = options[0].get("id")
    if not choice or choice == "any":
        return first_id if isinstance(first_id, str) else None
    keywords = _SPLIT_KEYWORDS.get(choice, ())
    for option in options:
        blob = normalize_exercise_name(
            f"{option.get('id', '')} {option.get('name', '')}"
        )
        if any(keyword in blob for keyword in keywords):
            option_id = option.get("id")
            return option_id if isinstance(option_id, str) else None
    return first_id if isinstance(first_id, str) else None


def _goal_for(plan: "PlanSession") -> str:
    if plan.sports and plan.gym_purpose != "general":
        return "performance"
    return "aesthetic"


@dataclass
class SportAnswer:
    name: str
    days: list[int] = field(default_factory=list)
    duration_min: int | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "days": self.days,
            "durationMin": self.duration_min,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "SportAnswer":
        raw_days = data.get("days", [])
        return cls(
            name=str(data.get("name", "")),
            days=(
                [int(day) for day in raw_days if isinstance(day, int)]
                if isinstance(raw_days, list)
                else []
            ),
            duration_min=_opt_int(data.get("durationMin")),
        )


@dataclass
class PlanSession:
    plan_request_id: uuid.UUID
    step: str = "sports"
    sports: list[SportAnswer] = field(default_factory=list)
    current_sport: int = 0
    gym_days: int | None = None
    gym_purpose: str | None = None
    split_choice: str | None = None
    plan: PlanSummaryOut | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class PlanResult:
    message: str
    request_id: uuid.UUID | None = None
    splits: list[PlanSplitOut] | None = None
    plan: PlanSummaryOut | None = None
    status: str = "question"  # question | ready | done | cancelled
    cleared: bool = False


def _opt_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _key(user_id: uuid.UUID) -> str:
    return f"{PLAN_KEY}:{user_id}"


def _dump(plan: PlanSession) -> str:
    return json.dumps(
        {
            "planRequestId": str(plan.plan_request_id),
            "step": plan.step,
            "sports": [sport.to_dict() for sport in plan.sports],
            "currentSport": plan.current_sport,
            "gymDays": plan.gym_days,
            "gymPurpose": plan.gym_purpose,
            "splitChoice": plan.split_choice,
            "plan": plan.plan.model_dump(mode="json") if plan.plan is not None else None,
            "createdAt": plan.created_at.isoformat(),
        }
    )


def _load(raw: str) -> PlanSession:
    data = json.loads(raw)
    plan_raw = data.get("plan")
    return PlanSession(
        plan_request_id=uuid.UUID(data["planRequestId"]),
        step=str(data.get("step", "sports")),
        sports=[SportAnswer.from_dict(item) for item in data.get("sports", []) or []],
        current_sport=_opt_int(data.get("currentSport")) or 0,
        gym_days=_opt_int(data.get("gymDays")),
        gym_purpose=(
            str(data["gymPurpose"]) if isinstance(data.get("gymPurpose"), str) else None
        ),
        split_choice=(
            str(data["splitChoice"]) if isinstance(data.get("splitChoice"), str) else None
        ),
        plan=(
            PlanSummaryOut.model_validate(plan_raw) if isinstance(plan_raw, dict) else None
        ),
        created_at=datetime.fromisoformat(data["createdAt"]),
    )


async def _persist(redis: aioredis.Redis, user_id: uuid.UUID, plan: PlanSession) -> None:
    await redis.setex(_key(user_id), settings.plan_session_ttl_seconds, _dump(plan))


async def get_plan(redis: aioredis.Redis, user_id: uuid.UUID) -> PlanSession | None:
    raw = await redis.get(_key(user_id))
    return _load(str(raw)) if raw is not None else None


async def start_plan(redis: aioredis.Redis, user_id: uuid.UUID) -> PlanSession:
    plan = PlanSession(plan_request_id=uuid.uuid4())
    await _persist(redis, user_id, plan)
    return plan


async def clear_plan(redis: aioredis.Redis, user_id: uuid.UUID) -> None:
    await redis.delete(_key(user_id))


def _question(
    plan: PlanSession, message: str, *, status: str = "question"
) -> PlanResult:
    return PlanResult(
        message=message,
        request_id=plan.plan_request_id,
        plan=plan.plan,
        status=status,
    )


def _weekdays_question(plan: PlanSession) -> str:
    sport = plan.sports[plan.current_sport]
    return (
        f"¿Qué días de la semana practicas {sport.name}? "
        "(dime los días, ej: «lunes y jueves» o «entre semana»)"
    )


def _duration_question(plan: PlanSession) -> str:
    sport = plan.sports[plan.current_sport]
    return (
        f"¿Cuánto dura cada sesión de {sport.name}? (ej: 90 minutos o 1.5 h) "
        "así lo tendré en cuenta para registrar tus sesiones."
    )


def _render_summary(plan: PlanSession) -> str:
    if plan.plan is None:
        return ""
    lines = []
    for day in plan.plan.days:
        label = day.label or _WEEKDAY_NAMES.get(day.day_of_week, "")
        if day.day_type == "deporte":
            name = day.discipline_name or day.label or "Deporte"
            duration = f" · {day.duration_min} min" if day.duration_min else ""
            lines.append(f"- {label}: {name}{duration}")
        elif day.day_type == "gimnasio":
            exercises = ", ".join(ex.name for ex in day.exercises)
            lines.append(f"- {label}: {exercises}")
        else:
            lines.append(f"- {label}: descanso")
    return "\n".join(lines)


def _summary_message(plan: PlanSession) -> str:
    return (
        f"Este es tu plan propuesto '{plan.plan.name if plan.plan else ''}':\n"
        f"{_render_summary(plan)}\n\n"
        "¿Confirmas que lo guardo? (responde «sí» o «no»)"
    )


def _resolve_discipline(
    sport_ref: str, disciplines: dict[str, Discipline]
) -> Discipline | None:
    normalized = normalize_exercise_name(sport_ref)
    if normalized in disciplines:
        return disciplines[normalized]
    target = _DISCIPLINE_ALIASES.get(normalized)
    if target is not None and target in disciplines:
        return disciplines[target]
    return disciplines.get("other")


def _build_summary(
    data: dict[str, object],
    catalog: dict[str, CatalogExercise],
    disciplines: dict[str, Discipline],
) -> PlanSummaryOut:
    raw_days = data.get("days")
    days: list[PlanDayOut] = []
    for raw in raw_days if isinstance(raw_days, list) else []:
        if not isinstance(raw, dict):
            continue
        day_of_week = _opt_int(raw.get("dayOfWeek"))
        if day_of_week is None or not (1 <= day_of_week <= 7):
            continue
        day_type = str(raw.get("dayType", "descanso")).lower()
        label = raw.get("label")
        label_str = str(label) if isinstance(label, str) and label.strip() else None
        duration = _opt_int(raw.get("durationMin"))
        if day_type == "deporte":
            sport_ref = raw.get("discipline") or label or ""
            discipline = (
                _resolve_discipline(str(sport_ref), disciplines)
                if isinstance(sport_ref, str) and sport_ref
                else None
            )
            days.append(
                PlanDayOut(
                    day_of_week=day_of_week,
                    day_type="deporte",
                    label=label_str,
                    discipline_id=discipline.id if discipline is not None else None,
                    discipline_name=(
                        discipline.name
                        if discipline is not None
                        else (label_str or str(sport_ref))
                    ),
                    duration_min=duration,
                )
            )
        elif day_type == "gimnasio":
            exercises: list[PlanExerciseOut] = []
            for raw_exercise in raw.get("exercises", []):
                if not isinstance(raw_exercise, dict):
                    continue
                name = raw_exercise.get("name")
                if not isinstance(name, str):
                    continue
                entry = catalog.get(normalize_exercise_name(name))
                if entry is None:
                    continue
                sets: list[PlanSetTargetOut] = []
                for raw_set in raw_exercise.get("sets", []):
                    if not isinstance(raw_set, dict):
                        continue
                    sets.append(
                        PlanSetTargetOut(
                            target_reps_min=_opt_int(raw_set.get("targetRepsMin")) or 8,
                            target_reps_max=_opt_int(raw_set.get("targetRepsMax")),
                            target_rest_seconds=_opt_int(raw_set.get("targetRestSeconds")),
                        )
                    )
                exercises.append(
                    PlanExerciseOut(
                        name=entry.name,
                        exercise_id=entry.id,
                        sets=sets or [PlanSetTargetOut(target_reps_min=8, target_reps_max=12)],
                    )
                )
            days.append(
                PlanDayOut(
                    day_of_week=day_of_week,
                    day_type="gimnasio",
                    label=label_str,
                    exercises=exercises,
                )
            )
        else:
            days.append(
                PlanDayOut(
                    day_of_week=day_of_week,
                    day_type="descanso",
                    label=label_str,
                )
            )
    name = data.get("name")
    return PlanSummaryOut(
        name=str(name).strip() if isinstance(name, str) and name.strip() else "Mi rutina",
        days=days,
    )


def _to_routine_in(plan: PlanSession) -> RoutineIn:
    assert plan.plan is not None
    days: list[RoutineDayIn] = []
    for day in plan.plan.days:
        if day.day_type == "deporte":
            days.append(
                RoutineDayIn(
                    day_of_week=day.day_of_week,
                    day_type="deporte",
                    label=day.label,
                    discipline_id=day.discipline_id,
                    target_duration_min=day.duration_min,
                )
            )
        elif day.day_type == "gimnasio":
            exercises = [
                RoutineExerciseIn(
                    exercise_id=exercise.exercise_id,
                    order_index=index,
                    sets=[
                        RoutineSetIn(
                            set_number=set_index + 1,
                            set_type="normal",
                            target_reps_min=workout_set.target_reps_min,
                            target_reps_max=workout_set.target_reps_max,
                            target_rest_seconds=workout_set.target_rest_seconds,
                        )
                        for set_index, workout_set in enumerate(exercise.sets)
                    ],
                )
                for index, exercise in enumerate(day.exercises)
                if exercise.exercise_id is not None
            ]
            days.append(
                RoutineDayIn(
                    day_of_week=day.day_of_week,
                    day_type="gimnasio",
                    label=day.label,
                    exercises=exercises,
                )
            )
        else:
            days.append(
                RoutineDayIn(
                    day_of_week=day.day_of_week,
                    day_type="descanso",
                    label=day.label,
                )
            )
    return RoutineIn(name=plan.plan.name, days=days)


async def _persist_plan(
    session: AsyncSession, user_id: uuid.UUID, plan: PlanSession
) -> Routine:
    return await routine_crud.create_routine(session, user_id, _to_routine_in(plan))


async def _generate_and_summarize(
    redis: aioredis.Redis,
    user_id: uuid.UUID,
    session: AsyncSession,
    plan: PlanSession,
) -> PlanResult:
    split_id: str | None = None
    if plan.gym_days and plan.gym_days > 0:
        options = await fetch_plan_splits(
            [sport.to_dict() for sport in plan.sports], plan.gym_days
        )
        split_id = _pick_split(options, plan.split_choice)
    goal = _goal_for(plan)
    catalog = await catalog_lookup(session)
    names = [entry.name for entry in catalog.values()]
    data = await fetch_plan_generate(
        [sport.to_dict() for sport in plan.sports],
        plan.gym_days or 0,
        split_id,
        goal,
        names,
    )
    disciplines = await routine_crud.list_disciplines(session)
    disciplines_map = {
        discipline.normalized_name: discipline for discipline in disciplines
    }
    plan.plan = _build_summary(data, catalog, disciplines_map)
    plan.step = "summary"
    await _persist(redis, user_id, plan)
    return _question(plan, _summary_message(plan), status="ready")


async def process_plan_message(
    redis: aioredis.Redis,
    user_id: uuid.UUID,
    session: AsyncSession,
    text: str,
) -> PlanResult | None:
    """Procesa un mensaje del chat dentro del flujo de creacion de plan.

    Devuelve None si no hay plan activo y el texto no es un trigger.
    """
    plan = await get_plan(redis, user_id)
    if plan is None:
        intent = plan_intent(text)
        if intent == "none":
            return None
        plan = await start_plan(redis, user_id)
        if intent == "clear":
            return _question(plan, _SPORTS_QUESTION)
        plan.step = "confirm"
        await _persist(redis, user_id, plan)
        return _question(plan, _CONFIRM_QUESTION)

    if plan.step == "confirm":
        if is_confirm(text) or plan_intent(text) == "clear":
            plan.step = "sports"
            await _persist(redis, user_id, plan)
            return _question(plan, _SPORTS_QUESTION)
        if is_cancel(text):
            await clear_plan(redis, user_id)
            return PlanResult(
                message=_CONFIRM_CANCELLED_MESSAGE,
                request_id=plan.plan_request_id,
                status="cancelled",
                cleared=True,
            )
        return _question(plan, _CONFIRM_QUESTION)

    if plan.step == "summary":
        if is_confirm(text):
            routine = await _persist_plan(session, user_id, plan)
            await clear_plan(redis, user_id)
            return PlanResult(
                message=f"¡Rutina '{routine.name}' guardada! Ya la tienes activa.",
                request_id=plan.plan_request_id,
                status="done",
                cleared=True,
            )
        if is_cancel(text):
            await clear_plan(redis, user_id)
            return PlanResult(
                message="Entendido, no he guardado nada.",
                request_id=plan.plan_request_id,
                status="cancelled",
                cleared=True,
            )
        return _question(plan, _summary_message(plan), status="ready")

    if plan.step == "sports":
        sports = parse_sports_answer(text)
        if sports is None:
            return _question(plan, _SPORTS_QUESTION)
        plan.sports = [SportAnswer(name=name) for name in sports]
        if not plan.sports:
            plan.step = "gym_purpose"
            await _persist(redis, user_id, plan)
            return _question(plan, _gym_purpose_question(plan))
        plan.current_sport = 0
        plan.step = "sport_weekdays"
        await _persist(redis, user_id, plan)
        return _question(plan, _weekdays_question(plan))

    if plan.step == "sport_weekdays":
        days = parse_weekdays_answer(text)
        if days is None:
            return _question(plan, _weekdays_question(plan))
        plan.sports[plan.current_sport].days = days
        plan.step = "sport_duration"
        await _persist(redis, user_id, plan)
        return _question(plan, _duration_question(plan))

    if plan.step == "sport_duration":
        duration = parse_duration_answer(text)
        if duration is None:
            return _question(plan, _duration_question(plan))
        plan.sports[plan.current_sport].duration_min = duration
        if plan.current_sport + 1 < len(plan.sports):
            plan.current_sport += 1
            plan.step = "sport_weekdays"
            await _persist(redis, user_id, plan)
            return _question(plan, _weekdays_question(plan))
        plan.current_sport = 0
        plan.step = "gym_purpose"
        await _persist(redis, user_id, plan)
        return _question(plan, _gym_purpose_question(plan))

    if plan.step == "gym_purpose":
        purpose = parse_gym_purpose_answer(text, plan.sports)
        if purpose is None:
            return _question(plan, _gym_purpose_question(plan))
        if purpose == "none":
            plan.gym_days = 0
            await _persist(redis, user_id, plan)
            return await _generate_and_summarize(redis, user_id, session, plan)
        plan.gym_purpose = purpose
        plan.step = "gym_days"
        await _persist(redis, user_id, plan)
        return _question(plan, _gym_days_question())

    if plan.step == "gym_days":
        gym_days = parse_gym_days_answer(text)
        if gym_days is None:
            return _question(plan, _gym_days_question())
        plan.gym_days = gym_days
        if gym_days > 0:
            plan.step = "gym_split"
            await _persist(redis, user_id, plan)
            return _question(plan, _SPLIT_QUESTION)
        await _persist(redis, user_id, plan)
        return await _generate_and_summarize(redis, user_id, session, plan)

    if plan.step == "gym_split":
        choice = parse_split_choice(text)
        if choice is None:
            return _question(plan, _SPLIT_QUESTION)
        plan.split_choice = choice
        await _persist(redis, user_id, plan)
        return await _generate_and_summarize(redis, user_id, session, plan)

    return _question(plan, "No he entendido esa respuesta. " + _question_for(plan))


def _question_for(plan: PlanSession) -> str:
    if plan.step == "confirm":
        return _CONFIRM_QUESTION
    if plan.step == "sports":
        return _SPORTS_QUESTION
    if plan.step == "sport_weekdays":
        return _weekdays_question(plan)
    if plan.step == "sport_duration":
        return _duration_question(plan)
    if plan.step == "gym_purpose":
        return _gym_purpose_question(plan)
    if plan.step == "gym_days":
        return _gym_days_question()
    if plan.step == "gym_split":
        return _SPLIT_QUESTION
    if plan.step == "summary":
        return _summary_message(plan)
    return _SPORTS_QUESTION


async def confirm_plan(
    redis: aioredis.Redis,
    user_id: uuid.UUID,
    session: AsyncSession,
    plan_request_id: uuid.UUID,
) -> PlanResult:
    plan = await get_plan(redis, user_id)
    if (
        plan is None
        or plan.plan_request_id != plan_request_id
        or plan.step != "summary"
    ):
        return PlanResult(
            message="No hay un plan pendiente para confirmar.",
            status="cancelled",
        )
    routine = await _persist_plan(session, user_id, plan)
    await clear_plan(redis, user_id)
    return PlanResult(
        message=f"¡Rutina '{routine.name}' guardada! Ya la tienes activa.",
        request_id=plan_request_id,
        status="done",
        cleared=True,
    )


async def cancel_plan(
    redis: aioredis.Redis,
    user_id: uuid.UUID,
    plan_request_id: uuid.UUID,
) -> PlanResult:
    plan = await get_plan(redis, user_id)
    if plan is None or plan.plan_request_id != plan_request_id:
        return PlanResult(
            message="No había ningún plan pendiente.",
            status="cancelled",
        )
    await clear_plan(redis, user_id)
    return PlanResult(
        message="Entendido, no he guardado nada.",
        request_id=plan_request_id,
        status="cancelled",
        cleared=True,
    )
