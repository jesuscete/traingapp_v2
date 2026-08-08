import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.crud import sessions
from app.models import TrainingSession
from app.schemas.session import SessionIn, SessionOut

router = APIRouter(prefix="/internal", tags=["internal"])


async def verify_internal_token(
    x_internal_token: Annotated[str | None, Header()] = None,
) -> None:
    if x_internal_token != settings.internal_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal token",
        )


class InternalSessionIn(BaseModel):
    userId: uuid.UUID
    session: SessionIn


@router.post(
    "/sessions",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_internal_token)],
)
async def create_session_internal(
    body: InternalSessionIn,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TrainingSession:
    return await sessions.create(session, body.userId, body.session)
