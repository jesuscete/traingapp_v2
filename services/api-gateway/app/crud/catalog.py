import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement

from app.analytics.catalog import normalize_exercise_name
from app.models import (
    ExerciseCatalog,
    RoutineExercise,
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


def _spanish_key(row: ExerciseCatalog) -> str | None:
    details = row.details or {}
    name_es = details.get("nameEs") if isinstance(details, dict) else None
    if not isinstance(name_es, str) or not name_es.strip():
        return None
    return normalize_exercise_name(name_es)


def _keyed_by_names[T](
    rows: Sequence[ExerciseCatalog], value: Callable[[ExerciseCatalog], T]
) -> dict[str, T]:
    """Indexa por `normalized_name` y, sin pisar claves existentes, por el nombre en español.

    La web muestra y envía `nameEs`, así que las búsquedas por nombre (impactos musculares,
    peso corporal, resolución de ejercicios) deben reconocer ambos.
    """
    keyed = {row.normalized_name: value(row) for row in rows}
    for row in rows:
        key = _spanish_key(row)
        if key is not None:
            keyed.setdefault(key, value(row))
    return keyed


async def _global_rows(session: AsyncSession) -> list[ExerciseCatalog]:
    result = await session.execute(
        select(ExerciseCatalog).where(ExerciseCatalog.owner_user_id.is_(None))
    )
    return list(result.scalars().all())


async def catalog_lookup(session: AsyncSession) -> dict[str, CatalogExercise]:
    """nombre normalizado (canónico o español) -> (id, uses_bodyweight, unilateral)."""
    return _keyed_by_names(
        await _global_rows(session),
        lambda row: CatalogExercise(
            id=row.id,
            name=row.name,
            uses_bodyweight=row.uses_bodyweight,
            unilateral=row.unilateral,
            curated=row.details is None,
        ),
    )


async def uses_bodyweight_map(session: AsyncSession) -> dict[str, bool]:
    """nombre normalizado -> usa peso corporal en el cálculo de volumen."""
    return _keyed_by_names(await _global_rows(session), lambda row: row.uses_bodyweight)


async def exercise_muscle_map(
    session: AsyncSession,
) -> dict[str, dict[str, float]]:
    """nombre normalizado -> {grupo muscular: activación} del catálogo."""
    return _keyed_by_names(await _global_rows(session), lambda row: row.muscle_map)


def _visible_to(user_id: uuid.UUID) -> ColumnElement[bool]:
    return or_(ExerciseCatalog.owner_user_id.is_(None), ExerciseCatalog.owner_user_id == user_id)


async def list_visible(session: AsyncSession, user_id: uuid.UUID) -> list[ExerciseCatalog]:
    """Catálogo global más los ejercicios personalizados del usuario."""
    result = await session.execute(
        select(ExerciseCatalog).where(_visible_to(user_id)).order_by(ExerciseCatalog.name)
    )
    return list(result.scalars().all())


async def exercise_visible(
    session: AsyncSession, user_id: uuid.UUID, exercise_id: uuid.UUID
) -> bool:
    found = await session.scalar(
        select(ExerciseCatalog.id).where(
            ExerciseCatalog.id == exercise_id, _visible_to(user_id)
        )
    )
    return found is not None


async def invisible_ids(
    session: AsyncSession, user_id: uuid.UUID, exercise_ids: set[uuid.UUID]
) -> set[uuid.UUID]:
    """Ids que no existen o pertenecen a otro usuario."""
    if not exercise_ids:
        return set()
    found = await session.scalars(
        select(ExerciseCatalog.id).where(
            ExerciseCatalog.id.in_(exercise_ids), _visible_to(user_id)
        )
    )
    return exercise_ids - set(found.all())


async def custom_lookup(
    session: AsyncSession, user_id: uuid.UUID
) -> dict[uuid.UUID, CatalogExercise]:
    """id -> ejercicio personalizado del usuario."""
    result = await session.execute(
        select(ExerciseCatalog).where(ExerciseCatalog.owner_user_id == user_id)
    )
    return {
        row.id: CatalogExercise(
            id=row.id,
            name=row.name,
            uses_bodyweight=row.uses_bodyweight,
            unilateral=row.unilateral,
        )
        for row in result.scalars().all()
    }


async def muscle_maps_for_user(
    session: AsyncSession, user_id: uuid.UUID
) -> tuple[dict[uuid.UUID, dict[str, float]], dict[str, dict[str, float]]]:
    """Mapas musculares (global + propios) por id y por nombre (canónico y español)."""
    rows = await list_visible(session, user_id)
    by_id = {row.id: row.muscle_map for row in rows}
    by_name = _keyed_by_names([r for r in rows if r.owner_user_id is None], lambda r: r.muscle_map)
    return by_id, by_name


class CustomExerciseNameTaken(Exception):
    """Ya existe un ejercicio global o propio con ese nombre."""


class DeleteResult(Enum):
    DELETED = "deleted"
    NOT_FOUND = "not_found"
    IN_USE = "in_use"


async def create_custom(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    name: str,
    muscle_map: dict[str, float],
    uses_bodyweight: bool,
    unilateral: bool,
    details: dict[str, object],
) -> ExerciseCatalog:
    normalized = normalize_exercise_name(name)
    clash = await session.scalar(
        select(ExerciseCatalog.id).where(
            ExerciseCatalog.normalized_name == normalized, _visible_to(user_id)
        )
    )
    if clash is not None:
        raise CustomExerciseNameTaken(name)
    exercise = ExerciseCatalog(
        name=name.strip(),
        normalized_name=normalized,
        owner_user_id=user_id,
        exercise_type="strength",
        muscle_map=muscle_map,
        uses_bodyweight=uses_bodyweight,
        unilateral=unilateral,
        images=[],
        details=details,
    )
    session.add(exercise)
    await session.commit()
    await session.refresh(exercise)
    return exercise


async def delete_custom(
    session: AsyncSession, user_id: uuid.UUID, exercise_id: uuid.UUID
) -> DeleteResult:
    exercise = await session.scalar(
        select(ExerciseCatalog).where(
            ExerciseCatalog.id == exercise_id, ExerciseCatalog.owner_user_id == user_id
        )
    )
    if exercise is None:
        return DeleteResult.NOT_FOUND
    in_routine = await session.scalar(
        select(RoutineExercise.id).where(RoutineExercise.exercise_id == exercise_id).limit(1)
    )
    if in_routine is not None:
        return DeleteResult.IN_USE
    await session.delete(exercise)
    await session.commit()
    return DeleteResult.DELETED


async def favorite_ids(session: AsyncSession, user_id: uuid.UUID) -> set[uuid.UUID]:
    rows = await session.scalars(
        select(UserFavoriteExercise.exercise_id).where(UserFavoriteExercise.user_id == user_id)
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
