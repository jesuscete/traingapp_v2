import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Discipline,
    Routine,
    RoutineDay,
    RoutineExercise,
    RoutineSet,
)
from app.schemas.routine import RoutineDayIn, RoutineDayUpsert, RoutineIn

_DAY_LOADS = (
    selectinload(RoutineDay.exercises)
    .selectinload(RoutineExercise.sets),
)

_ROUTINE_LOADS = (
    selectinload(Routine.days)
    .selectinload(RoutineDay.exercises)
    .selectinload(RoutineExercise.sets),
)


def _build_day(
    day_of_week: int, data: RoutineDayIn | RoutineDayUpsert
) -> RoutineDay:
    day = RoutineDay(
        day_of_week=day_of_week,
        day_type=data.day_type,
        label=data.label,
        discipline_id=data.discipline_id,
        target_duration_min=data.target_duration_min,
        notes=data.notes,
    )
    for index, exercise in enumerate(data.exercises):
        routine_exercise = RoutineExercise(
            exercise_id=exercise.exercise_id,
            order_index=exercise.order_index or index,
            superset_group_id=exercise.superset_group_id,
        )
        for set_in in exercise.sets:
            routine_exercise.sets.append(
                RoutineSet(
                    set_number=set_in.set_number,
                    set_type=set_in.set_type,
                    target_reps_min=set_in.target_reps_min,
                    target_reps_max=set_in.target_reps_max,
                    target_rest_seconds=set_in.target_rest_seconds,
                )
            )
        day.exercises.append(routine_exercise)
    return day


async def get_active_routine(
    session: AsyncSession, user_id: uuid.UUID
) -> Routine | None:
    result = await session.execute(
        select(Routine)
        .where(Routine.user_id == user_id, Routine.is_active.is_(True))
        .options(*_ROUTINE_LOADS)
    )
    return result.scalar_one_or_none()


async def get_routine(
    session: AsyncSession, user_id: uuid.UUID, routine_id: uuid.UUID
) -> Routine | None:
    result = await session.execute(
        select(Routine)
        .where(Routine.id == routine_id, Routine.user_id == user_id)
        .options(*_ROUTINE_LOADS)
    )
    return result.scalar_one_or_none()


async def list_routines(
    session: AsyncSession, user_id: uuid.UUID
) -> list[Routine]:
    result = await session.execute(
        select(Routine)
        .where(Routine.user_id == user_id)
        .order_by(Routine.created_at.desc())
        .options(*_ROUTINE_LOADS)
    )
    return list(result.scalars().all())


async def create_routine(
    session: AsyncSession, user_id: uuid.UUID, data: RoutineIn
) -> Routine:
    await session.execute(
        update(Routine).where(Routine.user_id == user_id).values(is_active=False)
    )
    routine = Routine(user_id=user_id, name=data.name, is_active=True)
    for day in data.days:
        routine.days.append(_build_day(day.day_of_week, day))
    session.add(routine)
    await session.commit()
    result = await session.execute(
        select(Routine).where(Routine.id == routine.id).options(*_ROUTINE_LOADS)
    )
    return result.scalar_one()


async def update_routine(
    session: AsyncSession,
    user_id: uuid.UUID,
    routine_id: uuid.UUID,
    *,
    name: str | None = None,
    is_active: bool | None = None,
) -> Routine | None:
    routine = await get_routine(session, user_id, routine_id)
    if routine is None:
        return None
    if is_active is True:
        await session.execute(
            update(Routine)
            .where(Routine.user_id == user_id, Routine.id != routine_id)
            .values(is_active=False)
        )
    if name is not None:
        routine.name = name
    if is_active is not None:
        routine.is_active = is_active
    await session.commit()
    return await get_routine(session, user_id, routine_id)


async def delete_routine(
    session: AsyncSession, user_id: uuid.UUID, routine_id: uuid.UUID
) -> bool:
    routine = await get_routine(session, user_id, routine_id)
    if routine is None:
        return False
    await session.delete(routine)
    await session.commit()
    return True


async def upsert_day(
    session: AsyncSession,
    user_id: uuid.UUID,
    routine_id: uuid.UUID,
    day_of_week: int,
    data: RoutineDayUpsert,
) -> Routine | None:
    routine = await get_routine(session, user_id, routine_id)
    if routine is None:
        return None
    existing = next(
        (day for day in routine.days if day.day_of_week == day_of_week), None
    )
    if existing is not None:
        routine.days.remove(existing)
        await session.delete(existing)
        await session.flush()
    routine.days.append(_build_day(day_of_week, data))
    await session.commit()
    return await get_routine(session, user_id, routine_id)


async def delete_day(
    session: AsyncSession,
    user_id: uuid.UUID,
    routine_id: uuid.UUID,
    day_of_week: int,
) -> Routine | None:
    routine = await get_routine(session, user_id, routine_id)
    if routine is None:
        return None
    day = next(
        (day for day in routine.days if day.day_of_week == day_of_week), None
    )
    if day is not None:
        routine.days.remove(day)
        await session.delete(day)
        await session.commit()
    return await get_routine(session, user_id, routine_id)


async def get_day(
    session: AsyncSession, routine_day_id: uuid.UUID
) -> RoutineDay | None:
    result = await session.execute(
        select(RoutineDay)
        .where(RoutineDay.id == routine_day_id)
        .options(*_DAY_LOADS)
    )
    return result.scalar_one_or_none()


async def get_day_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    routine_day_id: uuid.UUID,
) -> RoutineDay | None:
    result = await session.execute(
        select(RoutineDay)
        .join(Routine, Routine.id == RoutineDay.routine_id)
        .where(RoutineDay.id == routine_day_id, Routine.user_id == user_id)
        .options(*_DAY_LOADS)
    )
    return result.scalar_one_or_none()


async def list_disciplines(session: AsyncSession) -> list[Discipline]:
    result = await session.execute(
        select(Discipline)
        .options(selectinload(Discipline.muscle_loads))
        .order_by(Discipline.category, Discipline.normalized_name)
    )
    return list(result.scalars().all())


async def get_discipline(
    session: AsyncSession, discipline_id: uuid.UUID
) -> Discipline | None:
    result = await session.execute(
        select(Discipline)
        .options(selectinload(Discipline.muscle_loads))
        .where(Discipline.id == discipline_id)
    )
    return result.scalar_one_or_none()
