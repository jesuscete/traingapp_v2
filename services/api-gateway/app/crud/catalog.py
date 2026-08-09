from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ExerciseCatalog


async def exercise_muscle_map(
    session: AsyncSession,
) -> dict[str, dict[str, float]]:
    """Mapa normalized_name -> {grupo muscular: activacion} del catalogo canonico."""
    result = await session.execute(select(ExerciseCatalog))
    return {row.normalized_name: row.muscles for row in result.scalars().all()}
