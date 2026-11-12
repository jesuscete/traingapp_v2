"""Redacción del análisis de deporte principal. El LLM no calcula: explica y prioriza."""

import json
import logging

from pydantic import BaseModel, Field

from app.llm import factory
from app.llm.base import LLMProvider
from app.llm.errors import LLMError
from app.llm.structured import generate, user_data, with_user_data_rule
from app.schemas.sport import SportNarrativeResponse

logger = logging.getLogger(__name__)

MAX_PRIORITIES = 5

SYSTEM_PROMPT = """
Eres un preparador físico especializado en deportes de combate y en fuerza aplicada.
Recibes un análisis YA CALCULADO del entrenamiento de un usuario frente a las demandas de su
deporte principal: patrones de movimiento (series/semana frente al objetivo), músculos,
zonas de repeticiones, equilibrio empuje/tirón, conflictos con los días de deporte y
carencias con ejercicios sugeridos.

Escribe en español, en tono directo de entrenador:
- "resumen": 2-3 frases con el diagnóstico (qué cubre bien y qué falta para su deporte).
- "prioridades": de 3 a 5 acciones concretas, ordenadas por impacto. Cita cifras del
  análisis y, cuando haya, nombres de los ejercicios sugeridos.

El análisis incluye "perfilDeporte": el perfil de referencia del deporte (cualidades,
patrones, reglas y prevención). Úsalo para justificar las prioridades; no lo contradigas.

Reglas: no inventes datos ni cifras que no estén en el análisis; no recalcules nada.
""".strip()


class LlmNarrative(BaseModel):
    resumen: str = Field(min_length=10)
    prioridades: list[str] = Field(min_length=1, max_length=MAX_PRIORITIES)


async def narrate_with_llm(
    provider: LLMProvider, sport_label: str, analysis: dict[str, object]
) -> SportNarrativeResponse:
    rendered = json.dumps(analysis, ensure_ascii=False, indent=1)
    narrative = await generate(
        provider,
        with_user_data_rule(SYSTEM_PROMPT),
        f"Deporte principal: {sport_label}.\n\n" + user_data(rendered),
        LlmNarrative,
    )
    return SportNarrativeResponse(
        source="llm",
        resumen=narrative.resumen.strip(),
        prioridades=[p.strip() for p in narrative.prioridades if p.strip()],
    )


def narrate_deterministic(sport_label: str, analysis: dict[str, object]) -> SportNarrativeResponse:
    score = analysis.get("score")
    gaps = analysis.get("gaps")
    messages = [
        str(g.get("message"))
        for g in (gaps if isinstance(gaps, list) else [])
        if isinstance(g, dict) and g.get("message")
    ]
    return SportNarrativeResponse(
        source="fallback",
        resumen=(
            f"Puntuación de preparación para {sport_label}: {score}/100. "
            f"Hay {len(messages)} aspectos a mejorar."
        ),
        prioridades=messages[:MAX_PRIORITIES] or ["Mantén la estructura actual."],
    )


async def narrate(sport_label: str, analysis: dict[str, object]) -> SportNarrativeResponse:
    provider = factory.get_provider()
    if provider is None:
        return narrate_deterministic(sport_label, analysis)
    try:
        return await narrate_with_llm(provider, sport_label, analysis)
    except LLMError:
        logger.exception("LLM sport narrative failed (%s); using fallback", provider.name)
        return narrate_deterministic(sport_label, analysis)
