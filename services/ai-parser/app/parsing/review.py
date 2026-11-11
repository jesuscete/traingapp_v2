import json

from pydantic import BaseModel, Field

from app.core.config import settings
from app.llm.base import LLMProvider
from app.llm.structured import generate, user_data, with_user_data_rule
from app.schemas.review import RoutineReviewResponse, Solapamiento

SYSTEM_PROMPT = """
Eres un coach de entrenamiento experto en periodización y equilibrio muscular.
Vas a evaluar la rutina semanal COMPLETA de un usuario (trabajo de gimnasio y
deportes combinados), NO la evalúes día a día: analiza la carga acumulada de
toda la semana y la interacción gimnasio + deporte.

Tu respuesta se valida contra un JSON Schema con tres campos, todo en español:
- "puntos_fuertes": lista de textos con lo que la rutina hace bien (equilibrio,
  descanso, variedad, progresión).
- "solapamientos": lista de objetos {"descripcion", "grupos", "dias"} con los
  solapamientos excesivos entre gimnasio y deporte (mismos grupos musculares en
  días iguales o muy próximos) y los grupos que acumulan demasiada carga semanal.
- "sugerencias": lista de cambios concretos y accionables (redistribuir días,
  subir o bajar volumen por grupo, mejorar el descanso entre grupos que se solapan).

Reglas:
- Sé específico: nombra grupos musculares y días cuando sea relevante.
- No inventes ejercicios ni datos que no estén en los datos del usuario.
""".strip()


class LlmRoutineReview(BaseModel):
    """Forma exacta que debe devolver el modelo (se pasa como JSON Schema)."""

    puntos_fuertes: list[str] = Field(default_factory=list)
    solapamientos: list[Solapamiento] = Field(default_factory=list)
    sugerencias: list[str] = Field(default_factory=list)


def build_user_prompt(payload: list[dict[str, object]]) -> str:
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    return (
        "Evaluación de la rutina de la semana. Cada item es un ejercicio o actividad con "
        "su día, tipo (gimnasio/deporte), grupos musculares implicados y volumen estimado "
        "(series/reps o duración).\n\n" + user_data(rendered)
    )


def _clean(items: list[str]) -> list[str]:
    return [item.strip() for item in items if item.strip()]


async def review_routine_with_llm(
    provider: LLMProvider, payload: list[dict[str, object]]
) -> RoutineReviewResponse:
    review = await generate(
        provider,
        with_user_data_rule(SYSTEM_PROMPT),
        build_user_prompt(payload),
        LlmRoutineReview,
        max_tokens=settings.llm_review_max_tokens,
    )
    return RoutineReviewResponse(
        puntos_fuertes=_clean(review.puntos_fuertes),
        solapamientos=[
            Solapamiento(
                descripcion=s.descripcion.strip(), grupos=_clean(s.grupos), dias=_clean(s.dias)
            )
            for s in review.solapamientos
            if s.descripcion.strip()
        ],
        sugerencias=_clean(review.sugerencias),
        source="llm",
    )
