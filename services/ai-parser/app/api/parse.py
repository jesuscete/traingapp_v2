from fastapi import APIRouter

from app.parsing.stub import parse_text
from app.schemas.parse import ParseRequest, ParseResponse

router = APIRouter(prefix="/parse", tags=["parse"])


@router.post("", response_model=ParseResponse)
async def parse(body: ParseRequest) -> ParseResponse:
    return parse_text(body.rawText)
