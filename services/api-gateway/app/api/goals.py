import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud.goals import list_goals
from app.models import User, UserGoal
from app.schemas.goal import GoalIn, GoalOut

router = APIRouter(prefix="/goals", tags=["goals"])
Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def goal_out(goal: UserGoal) -> GoalOut:
    out = GoalOut.model_validate(goal)
    if goal.target_date is not None:
        out.days_left = (goal.target_date - datetime.now(UTC).date()).days
    return out


async def _own(session: AsyncSession, user_id: uuid.UUID, goal_id: uuid.UUID) -> UserGoal:
    goal = await session.get(UserGoal, goal_id)
    if goal is None or goal.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Objetivo no encontrado")
    return goal


async def _clear_primary(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(
        update(UserGoal).where(UserGoal.user_id == user_id).values(is_primary=False)
    )


@router.get("", response_model=list[GoalOut])
async def get_goals(db: Db, user: CurrentUser) -> list[GoalOut]:
    return [goal_out(g) for g in await list_goals(db, user.id)]


@router.post("", response_model=GoalOut, status_code=status.HTTP_201_CREATED)
async def create_goal(body: GoalIn, db: Db, user: CurrentUser) -> GoalOut:
    has_primary = any(g.is_primary and not g.done for g in await list_goals(db, user.id))
    if body.is_primary:
        await _clear_primary(db, user.id)
    goal = UserGoal(user_id=user.id, **body.model_dump())
    if not has_primary and not body.done:
        goal.is_primary = True  # la primera meta activa pasa a ser la principal
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return goal_out(goal)


@router.put("/{goal_id}", response_model=GoalOut)
async def update_goal(goal_id: uuid.UUID, body: GoalIn, db: Db, user: CurrentUser) -> GoalOut:
    goal = await _own(db, user.id, goal_id)
    if body.is_primary and not goal.is_primary:
        await _clear_primary(db, user.id)
    for field, value in body.model_dump().items():
        setattr(goal, field, value)
    await db.commit()
    await db.refresh(goal)
    return goal_out(goal)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(goal_id: uuid.UUID, db: Db, user: CurrentUser) -> None:
    goal = await _own(db, user.id, goal_id)
    await db.delete(goal)
    await db.commit()
