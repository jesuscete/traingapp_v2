import hashlib
import json
import logging
import uuid
from typing import Annotated, Literal

import httpx
import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Query
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.sport import fetch_sport_narrative
from app.models import User
from app.schemas.sport_analysis import (
    RecommendationOut,
    SportAnalysisOut,
    SportNarrativeOut,
    TargetStatusOut,
    WeekFeedbackOut,
)
from app.services import recommendations, sport_analysis, sport_registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/sport", response_model=SportAnalysisOut)
async def analyze_sport(
    session: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    current_user: Annotated[User, Depends(get_current_user)],
    sport: Annotated[str | None, Query(max_length=40)] = None,
    weeks: Annotated[int, Query(ge=1, le=12)] = 4,
    basis: Literal["auto", "historial", "rutina"] = "auto",
    narrative: bool = False,
    routine_id: Annotated[uuid.UUID | None, Query(alias="routineId")] = None,
) -> SportAnalysisOut:
    """Carencias y desequilibrios frente al deporte principal (determinista).

    Con `narrative=true`, Claude redacta el diagnóstico y las prioridades a partir del
    análisis ya calculado; si la IA no está disponible se devuelve un resumen básico.
    """
    result = await sport_analysis.analyze_user(
        session, current_user, sport=sport, weeks=weeks, basis=basis, routine_id=routine_id
    )
    if narrative and result.basis != "sin_datos":
        result.narrative = await _narrative(result, redis)
    return result


@router.get("/recommend", response_model=RecommendationOut)
async def recommend_for_goal(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    goal: Annotated[str | None, Query(max_length=40)] = None,
    text: Annotated[str | None, Query(max_length=300)] = None,
    sport: Annotated[str | None, Query(max_length=40)] = None,
) -> RecommendationOut:
    """Ejercicios para un objetivo («mejorar la pegada»): mapa del deporte, sin IA."""
    return await recommendations.recommend(
        session, current_user, text=text, goal_key=goal, sport=sport
    )


@router.get("/week-feedback", response_model=WeekFeedbackOut)
async def week_feedback(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> WeekFeedbackOut:
    """Frase tras terminar un entreno: lo que más falta esta semana para el objetivo."""
    return await sport_analysis.week_feedback_for(session, current_user)


NARRATIVE_CACHE_PREFIX = "analysis:narrative"
NARRATIVE_CACHE_TTL = 24 * 3600


def narrative_payload(result: SportAnalysisOut) -> dict[str, object]:
    """Lo mínimo que necesita la redacción (M10): solo lo que no está bien, sin ids ni URLs."""

    def off_target(items: list[TargetStatusOut]) -> list[dict[str, object]]:
        return [
            {"que": t.label, "valor": t.value, "min": t.low, "max": t.high, "estado": t.status}
            for t in items
            if t.status != "ok"
        ]

    return {
        "score": result.score,
        "base": result.basis,
        "semanas": result.weeks,
        "patrones": off_target(result.patterns),
        "musculos": off_target(result.muscles),
        "zonasReps": off_target(result.rep_zones),
        "empuje": result.push_sets,
        "tiron": result.pull_sets,
        "gaps": [
            {
                "message": g.message,
                "gravedad": g.severity,
                "ejercicios": [x.name for x in g.suggestions],
            }
            for g in result.gaps[:6]
        ],
        "adherenciaPct": result.adherence.pct if result.adherence else None,
        # El conocimiento del deporte viaja ya resumido: Claude no tiene que deducirlo.
        "perfilDeporte": sport_registry.compact_summary(result.sport),
    }


async def _narrative(result: SportAnalysisOut, redis: aioredis.Redis) -> SportNarrativeOut:
    payload = narrative_payload(result)
    digest = hashlib.sha256(
        json.dumps([result.label, payload], sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:24]
    key = f"{NARRATIVE_CACHE_PREFIX}:{digest}"
    cached = await redis.get(key)
    if cached:
        return SportNarrativeOut.model_validate_json(cached)
    try:
        narrative = SportNarrativeOut.model_validate(
            await fetch_sport_narrative(result.label, payload)
        )
        if narrative.source == "llm":
            await redis.setex(key, NARRATIVE_CACHE_TTL, narrative.model_dump_json())
        return narrative
    except (httpx.HTTPError, ValueError, ValidationError):
        logger.exception("Sport narrative unavailable; using basic summary")
        return SportNarrativeOut(
            source="fallback",
            resumen=f"Puntuación de preparación para {result.label}: {result.score}/100.",
            prioridades=[g.message for g in result.gaps[:5]] or ["Mantén la estructura actual."],
        )
