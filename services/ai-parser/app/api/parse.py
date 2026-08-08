from fastapi import APIRouter

from app.parsing.service import parse_workout
from app.schemas.parse import ParseRequest, ParseResponse

router = APIRouter(prefix="/parse", tags=["parse"])


@router.post("", response_model=ParseResponse)
async def parse(body: ParseRequest) -> ParseResponse:
    return await parse_workout(body.rawText)
