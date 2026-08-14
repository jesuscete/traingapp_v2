import json
import logging
import re

from app.llm.base import LLMProvider
from app.parsing.plan_stub import normalize_name
from app.schemas.plan import (
    PlanDay,
    PlanExercise,
    PlanResponse,
    PlanSetTarget,
    SplitOption,
    SplitResponse,
    SportIn,
)

logger = logging.getLogger(__name__)

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)

SPLIT_SYSTEM_PROMPT = """
Eres un coach experto en programación de entrenamiento.
Dado el contexto semanal de un usuario (deportes con sus días y duración, y
días de gimnasio disponibles), propones 2-3 opciones de SPLIT de gimnasio.

Reglas:
- Devuelve SIEMPRE un único objeto JSON, sin texto antes ni después.
- El JSON tiene EXACTAMENTE esta estructura:
  {"options": [{"id": "torso_pierna_2x", "name": "Torso/Pierna x2", "description": "..."}]}
- Cada opción: id corto sin espacios, name legible y description que explica
  la distribución y cómo se compagina con los días de deporte (por ejemplo,
  evitar cargar pierna el día antes de una sesión de deporte).
- Las opciones deben encajar con los días de gimnasio disponibles (nunca pedir
  más días de los libres).
- Escribe todo en español.
- No añadas claves extra.
""".strip()

PLAN_SYSTEM_PROMPT = """
Eres un coach experto en programación de entrenamiento y periodización.
Vas a generar una rutina semanal completa combinando deporte(s) y gimnasio.

Contexto que recibirás en el mensaje de usuario:
- Deportes con sus días y duración por sesión (esos días ya están reservados).
- Días de gimnasio disponibles (días libres de deporte).
- Split elegido por el usuario.
- Objetivo: "aesthetic" (prioriza gimnasio / verse bien) o "performance"
  (prioriza el rendimiento en el deporte practicado).
- Catálogo de ejercicios de gimnasio (elige SOLO de esta lista).

Reglas:
- Devuelve SIEMPRE un único objeto JSON, sin texto antes ni después.
- Estructura EXACTA:
  {"name": "...", "days": [{"dayOfWeek": 1, "dayType": "deporte|gimnasio|descanso",
    "label": "...", "discipline": "...", "durationMin": 45,
    "exercises": [{"name": "Press banca",
      "sets": [{"targetRepsMin": 8, "targetRepsMax": 12}]}]}]}
- Los días de deporte se reservan tal cual: discipline = nombre normalizado del
  deporte, durationMin = duración de la sesión, sin exercises.
- Los días de gimnasio usan SOLO ejercicios del catálogo recibido, 3-5
  ejercicios por día y 3-4 series cada uno con rango de repeticiones objetivo
  (rangos bajos para rendimiento, altos para estética).
- Añade ejercicios de apoyo al deporte cuando el objetivo sea "performance":
  core/rotación para deportes de combate, fuerza de piernas para corredores,
  etc.
- dayOfWeek: 1=lunes ... 7=domingo. Reserva descanso en los días libres que no
  se usen para gimnasio.
- No inventes ejercicios fuera del catálogo.
- Escribe todo en español.
- No añadas claves extra.
""".strip()


def _sport_discipline(name: str) -> str:
    return normalize_name(name)


async def suggest_splits_with_llm(
    provider: LLMProvider, sports: list[SportIn], gym_days: int
) -> SplitResponse:
    user_prompt = json.dumps(
        {
            "deportes": [
                {
                    "nombre": sport.name,
                    "dias": sport.days,
                    "duracionMin": sport.duration_min,
                }
                for sport in sports
            ],
            "diasGimnasio": gym_days,
        },
        ensure_ascii=False,
        indent=2,
    )
    content = await provider.complete(SPLIT_SYSTEM_PROMPT, user_prompt)
    data = _parse_json(content)
    options: list[SplitOption] = []
    for raw in _as_list(data.get("options")):
        if not isinstance(raw, dict):
            continue
        option_id = raw.get("id")
        name = raw.get("name")
        description = raw.get("description")
        if (
            not isinstance(option_id, str)
            or not option_id.strip()
            or not isinstance(name, str)
            or not name.strip()
            or not isinstance(description, str)
            or not description.strip()
        ):
            continue
        options.append(
            SplitOption(
                id=option_id.strip(),
                name=name.strip(),
                description=description.strip(),
            )
        )
    if not options:
        raise ValueError("LLM returned no valid split options")
    return SplitResponse(options=options[:3])


async def generate_plan_with_llm(
    provider: LLMProvider,
    sports: list[SportIn],
    gym_days: int,
    split_id: str | None,
    goal: str,
    catalog: list[str],
) -> PlanResponse:
    occupied = set()
    for sport in sports:
        occupied.update(sport.days)
    free_days = sorted(day for day in range(1, 8) if day not in occupied)
    user_prompt = json.dumps(
        {
            "deportes": [
                {
                    "nombre": sport.name,
                    "dias": sport.days,
                    "duracionMin": sport.duration_min,
                }
                for sport in sports
            ],
            "diasGimnasio": gym_days,
            "diasLibres": free_days,
            "split": split_id,
            "objetivo": goal,
            "catalogoEjercicios": catalog,
        },
        ensure_ascii=False,
        indent=2,
    )
    content = await provider.complete(PLAN_SYSTEM_PROMPT, user_prompt)
    data = _parse_json(content)
    return _plan_from(data, catalog, sports)


def _plan_from(
    data: dict[str, object], catalog: list[str], sports: list[SportIn]
) -> PlanResponse:
    catalog_set = {normalize_name(name) for name in catalog}
    days: list[PlanDay] = []
    for raw in _as_list(data.get("days")):
        if not isinstance(raw, dict):
            continue
        day = _day_from(raw, catalog_set, sports)
        if day is not None:
            days.append(day)
    name = data.get("name")
    return PlanResponse(
        name=str(name).strip() if isinstance(name, str) and name.strip() else "Mi rutina",
        days=days,
    )


def _day_from(
    raw: dict[str, object], catalog_set: set[str], sports: list[SportIn]
) -> PlanDay | None:
    day_of_week = _opt_int(raw.get("dayOfWeek"))
    if day_of_week is None or not (1 <= day_of_week <= 7):
        return None
    day_type = str(raw.get("dayType", "")).lower()
    if day_type not in ("gimnasio", "deporte", "descanso"):
        day_type = "descanso"
    label = raw.get("label")
    discipline = raw.get("discipline")
    duration = _opt_int(raw.get("durationMin"))
    exercises: list[PlanExercise] = []
    if day_type == "gimnasio":
        for raw_exercise in _as_list(raw.get("exercises")):
            if not isinstance(raw_exercise, dict):
                continue
            name = raw_exercise.get("name")
            if not isinstance(name, str):
                continue
            norm = normalize_name(name)
            if norm not in catalog_set:
                continue
            sets = [
                PlanSetTarget(
                    target_reps_min=_opt_int(item.get("targetRepsMin")) or 8,
                    target_reps_max=_opt_int(item.get("targetRepsMax")),
                    target_rest_seconds=_opt_int(item.get("targetRestSeconds")),
                )
                for item in _as_list(raw_exercise.get("sets"))
                if isinstance(item, dict)
            ]
            if not sets:
                sets = [PlanSetTarget(target_reps_min=8, target_reps_max=12)]
            exercises.append(PlanExercise(name=name, sets=sets))
        if not exercises:
            return None
    elif day_type == "deporte":
        if not discipline or not isinstance(discipline, str):
            sport = next((s for s in sports if day_of_week in s.days), None)
            discipline = _sport_discipline(sport.name) if sport is not None else ""
        else:
            discipline = normalize_name(discipline)
        if not discipline:
            return None
        if duration is None:
            sport = next((s for s in sports if day_of_week in s.days), None)
            duration = sport.duration_min if sport is not None else None
    return PlanDay(
        day_of_week=day_of_week,
        day_type=day_type,
        label=str(label) if isinstance(label, str) and label.strip() else None,
        discipline=discipline,
        duration_min=duration,
        exercises=exercises,
    )


def _parse_json(content: str) -> dict[str, object]:
    match = _JSON_OBJECT.search(content)
    if match is None:
        raise ValueError("LLM response contained no JSON object")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("LLM response JSON was not an object")
    return data


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _opt_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None
