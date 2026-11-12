from fastapi import APIRouter

from app.parsing.meal import parse_meal
from app.parsing.service import parse_workout
from app.schemas.meal import MealParseRequest, MealParseResponse
from app.schemas.parse import ParseRequest, ParseResponse

router = APIRouter(prefix="/parse", tags=["parse"])


@router.post("", response_model=ParseResponse)
async def parse(body: ParseRequest) -> ParseResponse:
    return await parse_workout(body.rawText)


@router.post("/meal", response_model=MealParseResponse)
async def parse_meal_endpoint(body: MealParseRequest) -> MealParseResponse:
    return await parse_meal(body.text)
