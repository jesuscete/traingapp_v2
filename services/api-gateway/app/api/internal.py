import hmac
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.sessions import session_out
from app.core.config import settings
from app.core.database import get_db
from app.crud import sessions, users
from app.schemas.gym import GymSessionOut
from app.schemas.session import SessionIn, SessionOut
from app.services import session_ingest

router = APIRouter(prefix="/internal", tags=["internal"])


async def verify_internal_token(
    x_internal_token: Annotated[str | None, Header()] = None,
) -> None:
    if x_internal_token is None or not hmac.compare_digest(
        x_internal_token.encode(), settings.internal_token.encode()
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal token",
        )


class InternalSessionIn(BaseModel):
    userId: uuid.UUID
    session: SessionIn


@router.post(
    "/sessions",
    response_model=GymSessionOut | SessionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_internal_token)],
)
async def create_session_internal(
    body: InternalSessionIn,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> GymSessionOut | SessionOut:
    user = await users.get_by_id(session, body.userId)
    weight_kg = user.weight_kg if user is not None else None
    record = await session_ingest.create_session(
        session, body.userId, body.session, weight_kg=weight_kg
    )
    reloaded = await sessions.get_for_user(session, record.id, body.userId)
    assert reloaded is not None
    return await session_out(session, reloaded)
