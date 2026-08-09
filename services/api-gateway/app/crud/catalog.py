import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExerciseCatalog


@dataclass(frozen=True)
class CatalogExercise:
    id: uuid.UUID
    name: str
    uses_bodyweight: bool
    unilateral: bool


async def catalog_lookup(session: AsyncSession) -> dict[str, CatalogExercise]:
    """normalized_name -> (id, uses_bodyweight, unilateral) del catalogo canonico."""
    result = await session.execute(select(ExerciseCatalog))
    return {
        row.normalized_name: CatalogExercise(
            id=row.id,
            name=row.name,
            uses_bodyweight=row.uses_bodyweight,
            unilateral=row.unilateral,
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
