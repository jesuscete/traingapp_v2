from typing import Annotated

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.redis import get_redis
from app.models import User
from app.schemas.agent import AgentActionResultOut, AgentMessageIn, AgentReplyOut
from app.services import agent
from app.services.agent_tools import ToolArgumentError, drop_action, load_action

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/message", response_model=AgentReplyOut)
async def agent_message(
    body: AgentMessageIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentReplyOut:
    """Un turno del entrenador conversacional (puede usar varias herramientas)."""
    return await agent.run_turn(session, redis, current_user, body.text)


@router.post("/actions/{action_id}/confirm", response_model=AgentActionResultOut)
async def confirm_agent_action(
    action_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> AgentActionResultOut:
    action = await load_action(redis, current_user.id, action_id)
    if action is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Propuesta caducada")
    try:
        message = await agent.confirm_action(session, current_user, action)
    except ToolArgumentError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
    await drop_action(redis, current_user.id, action_id)
    return AgentActionResultOut(message=message)


@router.delete("/actions/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
async def discard_agent_action(
    action_id: str,
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    await drop_action(redis, current_user.id, action_id)


@router.delete("/conversation", status_code=status.HTTP_204_NO_CONTENT)
async def reset_conversation(
    redis: Annotated[aioredis.Redis, Depends(get_redis)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    await agent.reset(redis, current_user.id)
