import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import gym as gym_analytics
from app.analytics.impacts import MuscleImpact, compute_muscle_impacts
from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud import gym as gym_crud
from app.crud.catalog import exercise_muscle_map
from app.models import TrainingSession, User
from app.schemas.gym import GymSessionIn, GymSessionOut, MuscleImpactOut

router = APIRouter(prefix="/sessions/gym", tags=["gym"])


def _to_out(
    record: TrainingSession,
    muscle_impacts: list[MuscleImpact],
) -> GymSessionOut:
    out = GymSessionOut.model_validate(record)
    details = record.details or {}
    calories = details.get("calories")
    out.calories = calories if isinstance(calories, (int, float)) else None
    out.muscle_impacts = [
        MuscleImpactOut(muscle_group=item.muscle_group, activation=item.activation)
        for item in muscle_impacts
    ]
    return out


async def _impacts_out(session: AsyncSession, record: TrainingSession) -> GymSessionOut:
    catalog = await exercise_muscle_map(session)
    flat = gym_analytics.flatten_workout_exercises(record.workout_exercises)
    return _to_out(record, compute_muscle_impacts(flat, catalog))


@router.post("", response_model=GymSessionOut, status_code=status.HTTP_201_CREATED)
async def create_gym_session(
    body: GymSessionIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GymSessionOut:
    record = await gym_crud.create_gym(
        session, current_user.id, body, weight_kg=current_user.weight_kg
    )
    return await _impacts_out(session, record)


@router.get("", response_model=list[GymSessionOut])
async def list_gym_sessions(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: int = 20,
    offset: int = 0,
) -> list[GymSessionOut]:
    records = await gym_crud.list_gym_by_user(
        session, current_user.id, limit=limit, offset=offset
    )
    catalog = await exercise_muscle_map(session)
    return [
        _to_out(
            record,
            compute_muscle_impacts(
                gym_analytics.flatten_workout_exercises(record.workout_exercises),
                catalog,
            ),
        )
        for record in records
    ]


@router.get("/{session_id}", response_model=GymSessionOut)
async def get_gym_session(
    session_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> GymSessionOut:
    record = await gym_crud.get_gym_for_user(session, session_id, current_user.id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gym session not found"
        )
    return await _impacts_out(session, record)
