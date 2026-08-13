from fastapi import APIRouter

from app.parsing.review_service import review_routine
from app.schemas.review import RoutineReviewRequest, RoutineReviewResponse

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.post("/routine", response_model=RoutineReviewResponse)
async def analyze_routine(body: RoutineReviewRequest) -> RoutineReviewResponse:
    return await review_routine(body.payload)