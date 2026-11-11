import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    ExerciseCatalog,
    TrainingSession,
    UserFavoriteExercise,
    WorkoutExercise,
    WorkoutSet,
)


@dataclass(frozen=True)
class CatalogExercise:
    id: uuid.UUID
    name: str
    uses_bodyweight: bool
    unilateral: bool
    curated: bool = False


async def catalog_lookup(session: AsyncSession) -> dict[str, CatalogExercise]:
    """normalized_name -> (id, uses_bodyweight, unilateral) del catalogo canonico."""
    result = await session.execute(select(ExerciseCatalog))
    return {
        row.normalized_name: CatalogExercise(
            id=row.id,
            name=row.name,
            uses_bodyweight=row.uses_bodyweight,
            unilateral=row.unilateral,
            curated=row.details is None,
        )
        for row in result.scalars().all()
    }


async def uses_bodyweight_map(session: AsyncSession) -> dict[str, bool]:
    """normalized_name -> usa peso corporal en el calculo de volumen."""
    result = await session.execute(
        select(ExerciseCatalog.normalized_name, ExerciseCatalog.uses_bodyweight)
    )
    return {name: value for name, value in result}


async def exercise_muscle_map(
    session: AsyncSession,
) -> dict[str, dict[str, float]]:
    """Mapa normalized_name -> {grupo muscular: activacion} del catalogo canonico."""
    result = await session.execute(select(ExerciseCatalog))
    return {row.normalized_name: row.muscle_map for row in result.scalars().all()}


async def exercise_exists(session: AsyncSession, exercise_id: uuid.UUID) -> bool:
    found = await session.scalar(
        select(ExerciseCatalog.id).where(ExerciseCatalog.id == exercise_id)
    )
    return found is not None


async def favorite_ids(session: AsyncSession, user_id: uuid.UUID) -> set[uuid.UUID]:
    rows = await session.scalars(
        select(UserFavoriteExercise.exercise_id).where(
            UserFavoriteExercise.user_id == user_id
        )
    )
    return set(rows.all())


async def set_favorite(
    session: AsyncSession, user_id: uuid.UUID, exercise_id: uuid.UUID, *, favorite: bool
) -> None:
    existing = await session.get(UserFavoriteExercise, (user_id, exercise_id))
    if favorite and existing is None:
        session.add(UserFavoriteExercise(user_id=user_id, exercise_id=exercise_id))
    elif not favorite and existing is not None:
        await session.delete(existing)
    await session.commit()


async def exercise_history(
    session: AsyncSession, user_id: uuid.UUID, exercise_id: uuid.UUID, *, limit: int
) -> list[tuple[TrainingSession, WorkoutExercise]]:
    """Apariciones del ejercicio en sesiones del usuario, de la más reciente a la más antigua."""
    rows = await session.execute(
        select(TrainingSession, WorkoutExercise)
        .join(WorkoutExercise, WorkoutExercise.session_id == TrainingSession.id)
        .where(
            TrainingSession.user_id == user_id,
            WorkoutExercise.exercise_id == exercise_id,
        )
        .options(selectinload(WorkoutExercise.sets).selectinload(WorkoutSet.entries))
        .order_by(TrainingSession.performed_at.desc(), WorkoutExercise.order_index)
        .limit(limit)
    )
    return [(ts, we) for ts, we in rows.tuples().all()]
