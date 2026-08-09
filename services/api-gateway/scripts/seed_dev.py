"""Seed de datos de desarrollo.

Limpia las sesiones de entrenamiento de la DB de desarrollo, crea un usuario
realista con perfil y genera un historico de 10 semanas de entrenamiento de
gimnasio periodizado (3 sesiones/semana). Al final verifica que los resumenes
(summary) y volumenes almacenados son coherentes.

Uso:
    E:\\nodejs\\node.exe ... (no aplica)
    python -m scripts.seed_dev
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timedelta

from sqlalchemy import delete, func, select

from app.analytics import kcal as kcal_analytics
from app.core.database import async_session_factory
from app.core.security import hash_password
from app.crud import gym as gym_crud
from app.models import Exercise, TrainingSession, User
from app.schemas.gym import (
    GymSessionIn,
    SetEntryIn,
    WorkoutExerciseIn,
    WorkoutSetIn,
)

SEED_EMAIL = "alex@traingapp.dev"
SEED_PASSWORD = "Traingapp#2026"

# Programas: (nombre, ejercicio, sets, reps, peso_inicial, incremento_por_bloque,
#             es_bodyweight, lastre_inicial)
PROGRAM: dict[str, list[tuple[str, str, int, int, float, float, bool, float]]] = {
    "PUSH": [
        ("Press banca", "Press banca", 4, 6, 60.0, 2.5, False, 0.0),
        ("Press militar", "Press militar", 3, 8, 35.0, 2.5, False, 0.0),
        ("Elevaciones laterales", "Elevaciones laterales", 3, 12, 8.0, 1.0, False, 0.0),
        ("Aperturas", "Aperturas", 3, 10, 12.0, 1.0, False, 0.0),
    ],
    "PULL": [
        ("Peso muerto", "Peso muerto", 5, 5, 80.0, 5.0, False, 0.0),
        ("Remo con barra", "Remo con barra", 4, 8, 50.0, 2.5, False, 0.0),
        ("Dominadas", "Dominadas", 4, 8, 0.0, 0.0, True, 2.5),
    ],
    "LEGS": [
        ("Sentadilla", "Sentadilla", 4, 6, 70.0, 5.0, False, 0.0),
        ("Prensa", "Prensa", 3, 10, 100.0, 7.5, False, 0.0),
        ("Peso muerto rumano", "Peso muerto rumano", 3, 10, 60.0, 2.5, False, 0.0),
    ],
}

WEEKDAYS = ["LUN", "MIS", "VIE"]
WEIGHTS: dict[str, list[float]] = {}

# Sesiones cardio: disciplina, texto, duracion (min), distancia (m), rpe,
# fc media, tipo de sesion, offset en semanas y dia del fin de semana.
CARDIO: list[dict[str, object]] = [
    {
        "discipline": "climbing",
        "raw_text": "Escalada de cuerda: vías de 5b-6a",
        "duration_minutes": 90,
        "rpe": 6,
        "week_offset": 0,
        "day": "sat",
        "exercises": [("Escalada", 90, None)],
    },
    {
        "discipline": "boxing",
        "raw_text": "Clase de boxeo con sparring",
        "duration_minutes": 90,
        "rpe": 9,
        "avg_heart_rate": 162.0,
        "week_offset": 0,
        "day": "sun",
        "exercises": [("Sparring", 45, None), ("Saco pesado", 45, None)],
    },
    {
        "discipline": "running",
        "raw_text": "Rodaje largo 15 km",
        "duration_minutes": 78,
        "distance_meters": 15000.0,
        "rpe": 7,
        "avg_heart_rate": 158.0,
        "workout_type": "long",
        "week_offset": 1,
        "day": "sat",
        "exercises": [("Carrera 15 km", 78, 15000.0)],
    },
    {
        "discipline": "climbing",
        "raw_text": "Boulder de 2 horas",
        "duration_minutes": 120,
        "rpe": 7,
        "week_offset": 1,
        "day": "sun",
        "exercises": [("Boulder", 120, None)],
    },
    {
        "discipline": "running",
        "raw_text": "Tempo run 5 km",
        "duration_minutes": 25,
        "distance_meters": 5000.0,
        "rpe": 8,
        "avg_heart_rate": 168.0,
        "workout_type": "tempo",
        "week_offset": 2,
        "day": "sat",
        "exercises": [("Carrera 5 km", 25, 5000.0)],
    },
    {
        "discipline": "boxing",
        "raw_text": "Boxeo: combos y saco pesado",
        "duration_minutes": 60,
        "rpe": 8,
        "avg_heart_rate": 150.0,
        "week_offset": 2,
        "day": "sun",
        "exercises": [("Saco pesado", 30, None), ("Sombra", 30, None)],
    },
    {
        "discipline": "running",
        "raw_text": "Carrera fácil 10 km",
        "duration_minutes": 55,
        "distance_meters": 10000.0,
        "rpe": 6,
        "avg_heart_rate": 152.0,
        "workout_type": "easy",
        "week_offset": 3,
        "day": "sat",
        "exercises": [("Carrera 10 km", 55, 10000.0)],
    },
]


def _base_monday() -> date:
    today = datetime.now().date()
    return today - timedelta(days=today.weekday())


def _dates_for_week(monday: date) -> list[datetime]:
    hour = time(18, 30)
    return [datetime.combine(monday + timedelta(days=offset), hour) for offset in (0, 2, 4)]


def _session_payload(
    label: str,
    performed_at: datetime,
    exercises: list[WorkoutExerciseIn],
    rpe: int,
) -> GymSessionIn:
    return GymSessionIn(
        raw_text=f"{label} {performed_at.strftime('%d/%m/%Y')}",
        performed_at=performed_at,
        duration_minutes=75,
        intensity=rpe,
        fatigue=6 if performed_at.weekday() == 4 else 5,
        exercises=exercises,
    )


def _exercise(
    name: str,
    sets: int,
    reps: int,
    weight: float,
    is_bodyweight: bool,
    added: float,
) -> WorkoutExerciseIn:
    ws: list[WorkoutSetIn] = []
    if is_bodyweight:
        # 1 serie de calentamiento sin lastre
        ws.append(
            WorkoutSetIn(
                set_number=1,
                is_warmup=True,
                entries=[SetEntryIn(entry_order=0, reps=reps, weight=0.0)],
            )
        )
        for n in range(1, sets + 1):
            ws.append(
                WorkoutSetIn(
                    set_number=n + 1,
                    entries=[
                        SetEntryIn(
                            entry_order=0,
                            reps=reps,
                            weight=max(0.0, added),
                            rpe=8,
                        )
                    ],
                )
            )
    else:
        ws.append(
            WorkoutSetIn(
                set_number=1,
                is_warmup=True,
                entries=[SetEntryIn(entry_order=0, reps=5, weight=0.4 * weight)],
            )
        )
        for n in range(1, sets + 1):
            ws.append(
                WorkoutSetIn(
                    set_number=n + 1,
                    entries=[
                        SetEntryIn(
                            entry_order=0,
                            reps=reps,
                            weight=weight,
                            rpe=8,
                        )
                    ],
                )
            )
    return WorkoutExerciseIn(name=name, order_index=0, sets=ws)


def _build_week(week_index: int) -> dict[str, list[WorkoutExerciseIn]]:
    block = week_index // 2
    plan: dict[str, list[WorkoutExerciseIn]] = {}
    for day, items in PROGRAM.items():
        exercises: list[WorkoutExerciseIn] = []
        for _, name, sets, reps, base, step, is_bw, lastre in items:
            weight = base + block * step
            exercises.append(_exercise(name, sets, reps, weight, is_bw, lastre))
        plan[day] = exercises
    return plan


async def _wipe_and_create_user() -> User:
    async with async_session_factory() as session:
        await session.execute(delete(TrainingSession))
        await session.execute(delete(User).where(User.email.in_([SEED_EMAIL])))
        user = User(
            email=SEED_EMAIL,
            hashed_password=hash_password(SEED_PASSWORD),
            name="Álex",
            weight_kg=78.0,
            height_cm=183.0,
            birth_year=1992,
            sex="male",
            fitness_level="intermediate",
            goal="performance",
        )
        session.add(user)
        await session.commit()
        return user


async def _build_cardio_sessions(
    user_id: object, monday: date, weight_kg: float | None
) -> int:
    """Crea sesiones de deporte (running, boxeo, escalada) en fines de semana."""
    records: list[TrainingSession] = []
    for item in CARDIO:
        day_offset = 5 if item["day"] == "sat" else 6
        performed_at = datetime.combine(
            monday + timedelta(days=day_offset - int(item["week_offset"]) * 7),
            time(9, 0),
        )
        exercises = [
            Exercise(
                name=name,
                duration_minutes=duration,
                distance_meters=distance,
                volume_kg=0.0,
            )
            for name, duration, distance in item["exercises"]  # type: ignore[union-attr]
        ]
        estimate = kcal_analytics.estimate(
            kcal_analytics.SessionKcalInput(
                discipline=item["discipline"],  # type: ignore[arg-type]
                weight_kg=weight_kg,
                duration_minutes=item["duration_minutes"],  # type: ignore[arg-type]
                rpe=item.get("rpe"),
                avg_heart_rate=item.get("avg_heart_rate"),
                workout_type=item.get("workout_type"),
                distance_meters=item.get("distance_meters"),
                exercises=tuple(
                    kcal_analytics.ExerciseInput(name=name)
                    for name, _, _ in item["exercises"]  # type: ignore[union-attr]
                ),
            )
        )
        details: dict[str, object] = {}
        if item.get("rpe") is not None:
            details["rpe"] = item.get("rpe")  # type: ignore[assignment]
        if item.get("avg_heart_rate") is not None:
            details["avgHeartRate"] = item.get("avg_heart_rate")  # type: ignore[assignment]
        details["kcal_confidence"] = estimate.confidence
        details["kcal_confidence_level"] = estimate.confidence_level
        details["kcal_factors"] = estimate.factors
        records.append(
            TrainingSession(
                user_id=user_id,
                discipline=item["discipline"],  # type: ignore[arg-type]
                raw_text=item["raw_text"],  # type: ignore[arg-type]
                performed_at=performed_at,
                duration_minutes=item["duration_minutes"],  # type: ignore[arg-type]
                distance_meters=item.get("distance_meters"),  # type: ignore[arg-type]
                estimated_kcal=estimate.kcal,
                volume_kg=0.0,
                details=details,
                exercises=exercises,
            )
        )
    async with async_session_factory() as session:
        session.add_all(records)
        await session.commit()
    return len(records)


async def main() -> None:
    print(f"[seed] limpiando sesiones y recreando usuario {SEED_EMAIL}")
    user = await _wipe_and_create_user()

    monday = _base_monday()
    total = 0
    async with async_session_factory() as session:
        for week in range(10):
            week_monday = monday - timedelta(days=(9 - week) * 7)
            plan = _build_week(week)
            for day, label in zip(WEEKDAYS, ["PUSH", "PULL", "LEGS"], strict=True):
                performed_at = _dates_for_week(week_monday)[WEEKDAYS.index(day)]
                if performed_at.date() > date.today():
                    continue
                payload = _session_payload(label, performed_at, plan[label], rpe=8)
                await gym_crud.create_gym(session, user.id, payload, weight_kg=user.weight_kg)
                total += 1
        await session.commit()

    print(f"[seed] creadas {total} sesiones de gimnasio (10 semanas x 3).")

    cardio_count = await _build_cardio_sessions(user.id, monday, user.weight_kg)
    print(f"[seed] creadas {cardio_count} sesiones de deporte (running/boxeo/escalada).")

    # Verificacion de resumenes
    async with async_session_factory() as session:
        count, volume_total = (
            await session.execute(
                select(
                    func.count(TrainingSession.id),
                    func.coalesce(func.sum(TrainingSession.volume_kg), 0),
                )
            )
        ).one()
        last_id = (
            await session.execute(
                select(TrainingSession.id)
                .where(TrainingSession.discipline == "gym")
                .order_by(TrainingSession.performed_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if last_id is None:
            raise RuntimeError("No hay sesiones tras el seed.")
        last = await gym_crud.get_gym_for_user(session, last_id, user.id)
        print(f"[verify] total sesiones: {count}, volumen acumulado: {volume_total:.1f} kg")
        if last is not None:
            summary = last.summary
            if summary is None:
                raise RuntimeError("La ultima sesion no tiene summary.")
            print(
                f"[verify] ultima sesion: {last.performed_at.date()}"
                f" | volumen={last.volume_kg:.1f} kg"
                f" | summary(total_volume={summary.total_volume:.1f},"
                f" sets={summary.sets_count},"
                f" avg_rpe={summary.avg_rpe}, duracion={summary.duration_min} min)"
                f" | ejercicios={len(last.workout_exercises)}"
            )
        else:
            raise RuntimeError("No se pudo recuperar la ultima sesion para verificar.")
    print("[seed] OK")


if __name__ == "__main__":
    asyncio.run(main())
