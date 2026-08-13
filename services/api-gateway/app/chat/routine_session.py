"""Sesion de rutina en vivo: resolucion de dia, prellenado y merge por texto.

Logica compartida entre la pestana de Chat y la de Seleccion manual
(`app/api/live.py` y `app/api/chat.py`):
- `resolve_routine_day`: a partir del texto del usuario ("he hecho el dia de
  piernas") devuelve el `RoutineDay` correspondiente sin forzar la
  coincidencia estricta calendario-rutina.
- `build_routine_exercises`: prellena la sesion con los ejercicios/series
  objetivo de ese dia (peso null + sugerido, seccion 5 del estudio).
- `merge_draft_into_live`: aplica una linea libre del chat (ej. "press banca
  80kg") sobre la sesion estructurada, actualizando series o anadiendo
  ejercicios no planificados.
"""

import uuid

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.catalog import normalize_exercise_name
from app.analytics.weight_suggestion import suggest_weight
from app.chat.conversation import (
    LiveExercise,
    LiveSet,
    extract_day_hint,
    extract_weekday,
    get_live,
    persist_live,
)
from app.crud.catalog import catalog_lookup
from app.crud.gym import weight_history
from app.models import Routine, RoutineDay
from app.schemas.chat import ExerciseDraftOut


def resolve_routine_day(routine: Routine, text: str) -> RoutineDay | None:
    """Resuelve el dia de rutina referenciado por el usuario.

    Prioridad: etiqueta mencionada ("dia de piernas") > dia de la semana
    mencionado ("el martes") > hoy. Si la etiqueta no coincide con ningun
    dia, no se fuerza coincidencia (devuelve None y se cae al flujo libre).
    """
    hint = extract_day_hint(text)
    if hint is not None:
        for day in routine.days:
            if day.label and hint in day.label.lower():
                return day
        return None

    weekday = extract_weekday(text)
    if weekday is not None:
        return next(
            (day for day in routine.days if day.day_of_week == weekday), None
        )

    from datetime import UTC, datetime

    today = datetime.now(UTC).isoweekday()
    return next((day for day in routine.days if day.day_of_week == today), None)


async def build_routine_exercises(
    session: AsyncSession, day: RoutineDay
) -> list[LiveExercise]:
    """Ejercicios/series objetivo de un dia de gimnasio, con peso sugerido."""
    catalog = await catalog_lookup(session)
    names: dict[uuid.UUID, str] = {entry.id: entry.name for entry in catalog.values()}
    bodyweight: set[uuid.UUID] = {
        entry.id for entry in catalog.values() if entry.uses_bodyweight
    }
    exercises: list[LiveExercise] = []
    for routine_exercise in day.exercises:
        history = (
            await weight_history(session, routine_exercise.exercise_id)
            if routine_exercise.exercise_id is not None
            else []
        )
        workout_sets: list[LiveSet] = []
        for routine_set in routine_exercise.sets:
            suggested = None
            if (
                routine_exercise.exercise_id is not None
                and routine_exercise.exercise_id not in bodyweight
            ):
                suggested = suggest_weight(history, routine_set.set_number)
            workout_sets.append(
                LiveSet(
                    set_number=routine_set.set_number,
                    set_type=routine_set.set_type,
                    target_reps_min=routine_set.target_reps_min,
                    target_reps_max=routine_set.target_reps_max,
                    suggested_weight=suggested,
                )
            )
        exercises.append(
            LiveExercise(
                name=(
                    names.get(routine_exercise.exercise_id, "")
                    if routine_exercise.exercise_id is not None
                    else ""
                ),
                exercise_id=routine_exercise.exercise_id,
                order_index=routine_exercise.order_index,
                routine_exercise_id=routine_exercise.id,
                sets=workout_sets,
            )
        )
    return exercises


def _reps_list(exercise: ExerciseDraftOut) -> list[int | None]:
    if exercise.per_set_reps:
        return list(exercise.per_set_reps)
    if exercise.sets:
        return [exercise.reps] * exercise.sets
    return [None]


async def merge_draft_into_live(
    redis: Redis,
    user_id: uuid.UUID,
    exercises: list[ExerciseDraftOut],
    session: AsyncSession,
) -> None:
    """Aplica una linea libre del chat sobre la sesion estructurada."""
    live = await get_live(redis, user_id)
    if live is None:
        return
    catalog = await catalog_lookup(session)
    changed = False
    for exercise in exercises:
        norm = normalize_exercise_name(exercise.name)
        target = next(
            (item for item in live.exercises if normalize_exercise_name(item.name) == norm),
            None,
        )
        catalog_entry = catalog.get(norm)
        reps_list = _reps_list(exercise)
        if target is None:
            live.exercises.append(
                LiveExercise(
                    name=catalog_entry.name if catalog_entry is not None else exercise.name,
                    exercise_id=catalog_entry.id if catalog_entry is not None else None,
                    order_index=len(live.exercises),
                    sets=[
                        LiveSet(
                            set_number=index + 1,
                            set_type="normal",
                            weight=exercise.weight_kg,
                            reps=reps,
                        )
                        for index, reps in enumerate(reps_list)
                    ],
                )
            )
            changed = True
            continue
        for index, reps in enumerate(reps_list):
            set_number = index + 1
            existing = next(
                (item for item in target.sets if item.set_number == set_number), None
            )
            if existing is not None:
                if exercise.weight_kg is not None:
                    existing.weight = exercise.weight_kg
                if reps is not None:
                    existing.reps = reps
            else:
                target.sets.append(
                    LiveSet(
                        set_number=set_number,
                        set_type="normal",
                        weight=exercise.weight_kg,
                        reps=reps,
                    )
                )
            changed = True
    if changed:
        await persist_live(redis, user_id, live)
