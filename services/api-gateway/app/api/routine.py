import logging
import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.review import fetch_routine_review
from app.crud import catalog as catalog_crud
from app.crud import routine as routine_crud
from app.crud.catalog import catalog_lookup
from app.models import Routine, User
from app.schemas.routine import (
    RoutineAddExerciseIn,
    RoutineDayIn,
    RoutineDayUpsert,
    RoutineIn,
    RoutineOut,
    RoutineSwapIn,
    RoutineUpdateIn,
)
from app.schemas.routine_review import RoutineReviewIn, RoutineReviewOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/routines", tags=["routines"])


async def _to_routine_out(session: AsyncSession, routine: Routine) -> RoutineOut:
    names = {entry.id: entry.name for entry in (await catalog_lookup(session)).values()}
    out = RoutineOut.model_validate(routine)
    for day_out in out.days:
        if day_out.discipline_id is not None:
            discipline = await routine_crud.get_discipline(session, day_out.discipline_id)
            day_out.discipline_name = discipline.name if discipline is not None else None
        for exercise_out in day_out.exercises:
            if exercise_out.exercise_id is not None:
                exercise_out.name = names.get(exercise_out.exercise_id)
    return out


async def _routine_or_404(
    session: AsyncSession, user_id: uuid.UUID, routine_id: uuid.UUID
) -> Routine:
    routine = await routine_crud.get_routine(session, user_id, routine_id)
    if routine is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Routine not found"
        )
    return routine


@router.get("", response_model=list[RoutineOut])
async def list_routines(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[RoutineOut]:
    routines = await routine_crud.list_routines(session, current_user.id)
    return [await _to_routine_out(session, routine) for routine in routines]


@router.get("/active", response_model=RoutineOut | None)
async def get_active_routine(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RoutineOut | None:
    routine = await routine_crud.get_active_routine(session, current_user.id)
    if routine is None:
        return None
    return await _to_routine_out(session, routine)


async def _ensure_exercises_visible(
    session: AsyncSession, user: User, days: Sequence[RoutineDayIn | RoutineDayUpsert]
) -> None:
    ids = {exercise.exercise_id for day in days for exercise in day.exercises}
    if await catalog_crud.invisible_ids(session, user.id, ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La rutina incluye ejercicios que no existen",
        )


@router.post("", response_model=RoutineOut, status_code=status.HTTP_201_CREATED)
async def create_routine(
    body: RoutineIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RoutineOut:
    await _ensure_exercises_visible(session, current_user, body.days)
    routine = await routine_crud.create_routine(session, current_user.id, body)
    return await _to_routine_out(session, routine)


@router.post("/review", response_model=RoutineReviewOut)
async def review_routine_draft(
    body: RoutineReviewIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RoutineReviewOut:
    """Evaluación por IA de una rutina (guardada o borrador). El payload estructurado
    lo construye el cliente; aquí solo se reenvía al evaluador (ai-parser)."""
    try:
        data = await fetch_routine_review(body.routineName, body.days)
    except Exception:
        logger.exception("Routine IA review failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="La evaluación por IA no está disponible ahora. Prueba en unos minutos.",
        ) from None
    return RoutineReviewOut.model_validate(data)


@router.put("/{routine_id}", response_model=RoutineOut)
async def update_routine(
    routine_id: uuid.UUID,
    body: RoutineUpdateIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RoutineOut:
    routine = await _routine_or_404(session, current_user.id, routine_id)
    updated = await routine_crud.update_routine(
        session,
        current_user.id,
        routine.id,
        name=body.name,
        is_active=body.is_active,
    )
    assert updated is not None
    return await _to_routine_out(session, updated)


async def _ensure_visible(session: AsyncSession, user: User, exercise_id: uuid.UUID) -> None:
    if await catalog_crud.invisible_ids(session, user.id, {exercise_id}):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Ejercicio no encontrado"
        )


@router.post("/{routine_id}/exercises/{routine_exercise_id}/swap", response_model=RoutineOut)
async def swap_routine_exercise(
    routine_id: uuid.UUID,
    routine_exercise_id: uuid.UUID,
    body: RoutineSwapIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RoutineOut:
    """Aplica una sustitución recomendada manteniendo series, objetivos y notas."""
    routine = await _routine_or_404(session, current_user.id, routine_id)
    await _ensure_visible(session, current_user, body.exercise_id)
    updated = await routine_crud.swap_exercise(
        session, routine, routine_exercise_id, body.exercise_id
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Routine exercise not found"
        )
    return await _to_routine_out(session, updated)


@router.post("/{routine_id}/days/{day_of_week}/exercises", response_model=RoutineOut)
async def add_routine_exercise(
    routine_id: uuid.UUID,
    day_of_week: Annotated[int, Path(ge=1, le=7)],
    body: RoutineAddExerciseIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RoutineOut:
    """Añade un ejercicio sugerido al final de un día de gimnasio."""
    routine = await _routine_or_404(session, current_user.id, routine_id)
    await _ensure_visible(session, current_user, body.exercise_id)
    updated = await routine_crud.add_exercise(
        session,
        routine,
        day_of_week,
        body.exercise_id,
        sets=body.sets,
        reps_min=body.target_reps_min,
        reps_max=max(body.target_reps_min, body.target_reps_max),
    )
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Ese día no es de gimnasio en la rutina",
        )
    return await _to_routine_out(session, updated)


MAX_ROUTINE_NAME = 120


@router.post(
    "/{routine_id}/duplicate", response_model=RoutineOut, status_code=status.HTTP_201_CREATED
)
async def duplicate_routine(
    routine_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RoutineOut:
    source = await _routine_or_404(session, current_user.id, routine_id)
    name = f"{source.name} (copia)"[:MAX_ROUTINE_NAME]
    copy = await routine_crud.duplicate_routine(session, current_user.id, source, name=name)
    return await _to_routine_out(session, copy)


@router.delete("/{routine_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_routine(
    routine_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    await _routine_or_404(session, current_user.id, routine_id)
    await routine_crud.delete_routine(session, current_user.id, routine_id)


@router.put("/{routine_id}/days/{day_of_week}", response_model=RoutineOut)
async def upsert_day(
    routine_id: uuid.UUID,
    day_of_week: Annotated[int, Path(ge=1, le=7)],
    body: RoutineDayUpsert,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RoutineOut:
    routine = await _routine_or_404(session, current_user.id, routine_id)
    await _ensure_exercises_visible(session, current_user, [body])
    updated = await routine_crud.upsert_day(
        session, current_user.id, routine.id, day_of_week, body
    )
    assert updated is not None
    return await _to_routine_out(session, updated)


@router.delete("/{routine_id}/days/{day_of_week}", response_model=RoutineOut)
async def delete_day(
    routine_id: uuid.UUID,
    day_of_week: Annotated[int, Path(ge=1, le=7)],
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RoutineOut:
    routine = await _routine_or_404(session, current_user.id, routine_id)
    updated = await routine_crud.delete_day(
        session, current_user.id, routine.id, day_of_week
    )
    assert updated is not None
    return await _to_routine_out(session, updated)