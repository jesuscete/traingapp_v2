"""Resolucion del perfil de entrenamiento (prompt de IA) para una rutina.

Elige el `TrainingPrompt` que la IA usara al generar el plan segun las
disciplinas que practica el usuario. Las disciplinas sin perfil asignado caen
en el prompt por defecto (`is_default = true`); si no hay prompts activos en
BBDD, devuelve `None` y el cliente usara el prompt estandar.
"""
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Discipline, DisciplineTrainingPrompt, TrainingPrompt

logger = logging.getLogger(__name__)


async def resolve_training_prompt(
    session: AsyncSession, discipline_names: list[str]
) -> TrainingPrompt | None:
    """Perfil para las disciplinas dadas.

    Prioriza el perfil de la primera disciplina (en orden del usuario) que tenga
    uno asignado y no sea el default; el default actua como fallback global.
    """
    if not discipline_names:
        return await _default_prompt(session)
    rows = await session.execute(
        select(Discipline.normalized_name, TrainingPrompt)
        .join(
            DisciplineTrainingPrompt,
            DisciplineTrainingPrompt.discipline_id == Discipline.id,
        )
        .join(
            TrainingPrompt,
            TrainingPrompt.id == DisciplineTrainingPrompt.training_prompt_id,
        )
        .where(
            Discipline.normalized_name.in_(discipline_names),
            TrainingPrompt.active.is_(True),
        )
    )
    by_discipline: dict[str, TrainingPrompt] = {}
    for normalized_name, prompt in rows.all():
        by_discipline.setdefault(normalized_name, prompt)
    for name in discipline_names:
        prompt = by_discipline.get(name)
        if prompt is not None and not prompt.is_default:
            return prompt
    return await _default_prompt(session)


async def _default_prompt(session: AsyncSession) -> TrainingPrompt | None:
    result = await session.execute(
        select(TrainingPrompt)
        .where(
            TrainingPrompt.is_default.is_(True),
            TrainingPrompt.active.is_(True),
        )
        .limit(1)
    )
    return result.scalar_one_or_none()
