import logging
import uuid
from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, Query
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.sport import fetch_sport_narrative
from app.models import User
from app.schemas.sport_analysis import SportAnalysisOut, SportNarrativeOut
from app.services import sport_analysis, sport_registry

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/sport", response_model=SportAnalysisOut)
async def analyze_sport(
    session: Annotated[AsyncSession, Depends(get_db)],
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
        result.narrative = await _narrative(result)
    return result


async def _narrative(result: SportAnalysisOut) -> SportNarrativeOut:
    payload = result.model_dump(mode="json", by_alias=True, exclude={"narrative"})
    # El conocimiento del deporte viaja ya resumido: Claude no tiene que deducirlo.
    payload["perfilDeporte"] = sport_registry.compact_summary(result.sport)
    try:
        return SportNarrativeOut.model_validate(
            await fetch_sport_narrative(result.label, payload)
        )
    except (httpx.HTTPError, ValueError, ValidationError):
        logger.exception("Sport narrative unavailable; using basic summary")
        return SportNarrativeOut(
            source="fallback",
            resumen=f"Puntuación de preparación para {result.label}: {result.score}/100.",
            prioridades=[g.message for g in result.gaps[:5]] or ["Mantén la estructura actual."],
        )
