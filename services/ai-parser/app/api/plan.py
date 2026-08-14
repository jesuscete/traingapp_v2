from fastapi import APIRouter

from app.parsing.plan_service import generate_plan, suggest_splits
from app.schemas.plan import (
    PlanGenerateIn,
    PlanResponse,
    SplitContextIn,
    SplitResponse,
)

router = APIRouter(prefix="/plan", tags=["plan"])


@router.post("/splits", response_model=SplitResponse)
async def plan_splits(body: SplitContextIn) -> SplitResponse:
    return await suggest_splits(body.sports, body.gym_days)

@router.post("/generate", response_model=PlanResponse)
async def plan_generate(body: PlanGenerateIn) -> PlanResponse:
    return await generate_plan(body)
