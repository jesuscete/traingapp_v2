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
        task="narrative",
    )
    return SportNarrativeResponse(
        source="llm",
        resumen=narrative.resumen.strip(),
        prioridades=[p.strip() for p in narrative.prioridades if p.strip()],
    )


SEVERITY_ORDER = {"alta": 0, "media": 1, "baja": 2}


def _first_rule(profile: object) -> str | None:
    """Primera regla de carga del perfil resumido («Reglas: …»), para la redacción sin IA."""
    if not isinstance(profile, str):
        return None
    for line in profile.splitlines():
        if line.startswith("Reglas: "):
            rule = line[len("Reglas: ") :].split(". ")[0].strip()
            return rule.rstrip(".") + "." if rule else None
    return None


def narrate_deterministic(sport_label: str, analysis: dict[str, object]) -> SportNarrativeResponse:
    """Redacción sin IA: diagnóstico por bandas, carencias por gravedad con ejercicios concretos
    y la regla de calendario más importante del deporte."""
    score = analysis.get("score")
    raw_gaps = analysis.get("gaps")
    gaps = [g for g in (raw_gaps if isinstance(raw_gaps, list) else []) if isinstance(g, dict)]
    gaps.sort(key=lambda g: SEVERITY_ORDER.get(str(g.get("gravedad") or g.get("severity")), 3))
    priorities: list[str] = []
    for gap in gaps:
        message = str(gap.get("message") or "").strip()
        if not message:
            continue
        exercises = gap.get("ejercicios")
        names = [str(e) for e in exercises][:2] if isinstance(exercises, list) else []
        priorities.append(message + (f" Prueba: {', '.join(names)}." if names else ""))
    rule = _first_rule(analysis.get("perfilDeporte"))
    if rule:
        priorities = priorities[: MAX_PRIORITIES - 1] + [f"Calendario: {rule}"]
    value = score if isinstance(score, int | float) else 0
    band = (
        "bien encaminada"
        if value >= 80
        else "aceptable, con carencias concretas"
        if value >= 60
        else "lejos de lo que pide tu deporte"
    )
    serious = sum(1 for g in gaps if str(g.get("gravedad") or g.get("severity")) == "alta")
    return SportNarrativeResponse(
        source="fallback",
        resumen=(
            f"Tu preparación para {sport_label} está {band} ({score}/100). "
            + (
                (
                    "Hay 1 carencia importante (empieza por ahí); el resto son de ajuste."
                    if serious == 1
                    else f"Hay {serious} carencias importantes; empieza por ellas."
                )
                if serious
                else "Lo que falta es de ajuste fino."
            )
        ),
        prioridades=priorities[:MAX_PRIORITIES] or ["Mantén la estructura actual."],
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
