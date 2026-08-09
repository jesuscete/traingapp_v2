import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import gym as gym_analytics
from app.analytics.impacts import compute_discipline_impacts, compute_muscle_impacts
from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud import sessions
from app.crud.catalog import exercise_muscle_map
from app.models import TrainingSession, User
from app.schemas.gym import GymSessionOut, MuscleImpactOut
from app.schemas.session import (
    MuscleImpactOut as LegacyMuscleImpactOut,
)
from app.schemas.session import (
    SessionIn,
    SessionListItem,
    SessionOut,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> TrainingSession:
    return await sessions.create(
        session, current_user.id, body, weight_kg=current_user.weight_kg
    )


@router.get("", response_model=list[SessionListItem])
async def list_sessions(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 20,
    offset: int = 0,
) -> list[TrainingSession]:
    return await sessions.list_by_user(
        session, current_user.id, limit=limit, offset=offset
    )


@router.get("/{session_id}", response_model=GymSessionOut | SessionOut)
async def get_session(
    session_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GymSessionOut | SessionOut:
    record = await sessions.get_for_user(session, session_id, current_user.id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    catalog = await exercise_muscle_map(session)
    if record.workout_exercises:
        flat = gym_analytics.flatten_workout_exercises(record.workout_exercises)
        impacts = compute_muscle_impacts(flat, catalog)
        out_gym = GymSessionOut.model_validate(record)
        details = record.details or {}
        calories = details.get("calories")
        out_gym.calories = calories if isinstance(calories, (int, float)) else None
        out_gym.muscle_impacts = [
            MuscleImpactOut(muscle_group=item.muscle_group, activation=item.activation)
            for item in impacts
        ]
        return out_gym
    impacts = compute_muscle_impacts(record.exercises, catalog)
    if not impacts:
        impacts = compute_discipline_impacts(record.discipline)
    out_legacy = SessionOut.model_validate(record)
    out_legacy.muscle_impacts = [
        LegacyMuscleImpactOut(muscle_group=item.muscle_group, activation=item.activation)
        for item in impacts
    ]
    return out_legacy


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    deleted = await sessions.delete_for_user(session, session_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
