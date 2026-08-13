import logging
from collections import Counter

from app.llm import factory
from app.parsing.review import review_routine_with_llm
from app.schemas.review import RoutineReviewResponse, Solapamiento

logger = logging.getLogger(__name__)


def review_routine_deterministic(
    payload: list[dict[str, object]],
) -> RoutineReviewResponse:
    """Fallback sin LLM: mensajes genéricos basados en la acumulación del payload."""
    counts: Counter[str] = Counter()
    gym_items = 0
    sport_items = 0
    day_mentions: list[dict[str, object]] = []
    for item in payload:
        if item.get("tipo") == "gimnasio":
            gym_items += 1
        elif item.get("tipo") == "deporte":
            sport_items += 1
        groups = item.get("gruposMusculares") or []
        day = item.get("diaSemana") or item.get("dia")
        for group in groups:
            counts[str(group)] += 1
        if day:
            day_mentions.append({
                "dia": str(day),
                "grupos": [str(group) for group in groups],
            })

    top_groups = [group for group, _ in counts.most_common(3)]

    puntos_fuertes: list[str] = []
    if gym_items and sport_items:
        puntos_fuertes.append(
            "Combinas trabajo de gimnasio y deporte, lo que aporta variedad de estímulos."
        )
    if top_groups:
        top_text = ", ".join(top_groups)
        puntos_fuertes.append(
            f"Grupos con más acumulación semanal: {top_text}."
        )
    if not puntos_fuertes:
        puntos_fuertes.append(
            "La rutina está equilibrada en cuanto a variedad de grupos musculares."
        )

    solapamientos: list[Solapamiento] = []
    if top_groups:
        dias: list[str] = [
            str(mention["dia"])
            for mention in day_mentions
            if top_groups[0] in [str(group) for group in mention["grupos"]]
        ]
        solapamientos.append(
            Solapamiento(
                descripcion=(
                    f"Alta acumulación semanal en {top_groups[0]}. Si el gimnasio y el "
                    "deporte lo trabajan en días iguales o muy próximos, reduce el volumen "
                    "de uno de los dos."
                ),
                grupos=top_groups[:2],
                dias=dias,
            )
        )

    sugerencias: list[str] = []
    if gym_items:
        sugerencias.append(
            "Distribuye los grupos de gimnasio dejando al menos 48h de descanso antes "
            "de la sesión de deporte que vuelva a cargarlos."
        )
    if sport_items:
        sugerencias.append(
            "Reduce el volumen de gimnasio en los grupos que más exige tu deporte "
            "los días previos a entrenarlo."
        )
    if not sugerencias:
        sugerencias.append(
            "Añade más variedad o descanso semanal para equilibrar la carga muscular."
        )

    return RoutineReviewResponse(
        puntos_fuertes=puntos_fuertes,
        solapamientos=solapamientos,
        sugerencias=sugerencias,
    )


async def review_routine(payload: list[dict[str, object]]) -> RoutineReviewResponse:
    """Evalúa la rutina con el LLM actual; sin proveedor o ante error, usa el stub."""
    provider = factory.get_provider()
    if provider is None:
        return review_routine_deterministic(payload)
    try:
        return await review_routine_with_llm(provider, payload)
    except Exception:
        logger.exception("LLM routine review failed; falling back to deterministic stub")
        return review_routine_deterministic(payload)