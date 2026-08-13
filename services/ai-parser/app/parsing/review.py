import json
import logging
import re
from typing import cast

from app.llm.base import LLMProvider
from app.schemas.review import RoutineReviewResponse, Solapamiento

logger = logging.getLogger(__name__)

_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)

SYSTEM_PROMPT = """
Eres un coach de entrenamiento experto en periodización y equilibrio muscular.
Vas a evaluar la rutina semanal COMPLETA de un usuario (trabajo de gimnasio y
deportes combinados), NO la evalúes día a día: analiza la carga acumulada de
toda la semana y la interacción gimnasio + deporte.

Reglas:
- Devuelve SIEMPRE un único objeto JSON válido, sin texto antes ni después.
- El JSON tiene EXACTAMENTE estas tres claves, cada una una lista de strings en español:
  - "puntos_fuertes": qué hace bien la rutina (equilibrio, descanso, variedad, progresión).
  - "solapamientos": solapamientos excesivos entre el trabajo de gimnasio y el deporte
    (mismos grupos musculares en días iguales o muy próximos) y grupos que acumulan
    demasiada carga semanal.
  - "sugerencias": cambios concretos y accionables (redistribuir días, subir o bajar
    volumen por grupo, mejorar el descanso entre grupos que se solapan).
- Sé específico: nombra grupos musculares y días cuando sea relevante.
- No inventes ejercicios ni datos que no estén en el payload.
- No añadas claves extra al JSON.
""".strip()


def build_user_prompt(payload: list[dict[str, object]]) -> str:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    return (
        "Evaluación de la rutina de la semana.\n\n"
        "EJERCICIOS / ACTIVIDADES DE LA SEMANA (JSON):\n"
        f"{rendered}\n\n"
        "Cada item representa un ejercicio o actividad con su día, tipo (gimnasio/deporte), "
        "grupos musculares implicados y volumen estimado (series/reps o duración). "
        "Evalúa la rutina COMPLETA en un único JSON con las tres claves indicadas."
    )


def _list_of_strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for part in value:
        if isinstance(part, str):
            item = part.strip()
            if item:
                items.append(item)
    return items


def _list_of_solapamientos(value: object) -> list[Solapamiento]:
    if not isinstance(value, list):
        return []
    items: list[Solapamiento] = []
    for part in value:
        if not isinstance(part, dict):
            continue
        descripcion = part.get("descripcion")
        if not isinstance(descripcion, str) or not descripcion.strip():
            continue
        items.append(
            Solapamiento(
                descripcion=descripcion.strip(),
                grupos=_list_of_strings(part.get("grupos")),
                dias=_list_of_strings(part.get("dias")),
            )
        )
    return items


async def review_routine_with_llm(
    provider: LLMProvider, payload: list[dict[str, object]]
) -> RoutineReviewResponse:
    content = await provider.complete(SYSTEM_PROMPT, build_user_prompt(payload))
    match = _JSON_OBJECT.search(content)
    if match is None:
        raise ValueError("LLM response contained no JSON object")
    data = json.loads(match.group(0))
    return _response_from(cast(dict[str, object], data))


def _response_from(data: dict[str, object]) -> RoutineReviewResponse:
    data = dict(data)
    for key in ("puntos_fuertes", "puntosFuertes"):
        if key in data:
            data["puntos_fuertes"] = data.pop(key)
    return RoutineReviewResponse(
        puntos_fuertes=_list_of_strings(data.get("puntos_fuertes")),
        solapamientos=_list_of_solapamientos(data.get("solapamientos")),
        sugerencias=_list_of_strings(data.get("sugerencias")),
    )