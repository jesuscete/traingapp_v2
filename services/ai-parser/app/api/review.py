from fastapi import APIRouter

from app.parsing.review_service import review_routine
from app.parsing.sport import narrate
from app.schemas.review import RoutineReviewRequest, RoutineReviewResponse
from app.schemas.sport import SportNarrativeRequest, SportNarrativeResponse

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("/routine", response_model=RoutineReviewResponse)
async def analyze_routine(body: RoutineReviewRequest) -> RoutineReviewResponse:
    return await review_routine(body.payload)


@router.post("/sport", response_model=SportNarrativeResponse)
async def analyze_sport(body: SportNarrativeRequest) -> SportNarrativeResponse:
    return await narrate(body.sport_label, body.analysis)
