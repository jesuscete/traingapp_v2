import asyncio
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from app.crud import sessions as sessions_crud
from app.crud import users as users_crud
from app.models import TrainingSession, WorkoutExercise
from app.schemas.session import SessionIn
from app.services.session_ingest import migrate_legacy_strength_sessions


def _legacy(discipline: str, exercises: list[dict[str, object]]) -> SessionIn:
    return SessionIn.model_validate(
        {
            "discipline": discipline,
            "raw_text": "legacy",
            "performed_at": datetime(2026, 8, 1, 18, tzinfo=UTC),
            "duration_minutes": 50,
            "exercises": exercises,
        }
    )


def test_migrates_only_legacy_strength_sessions(
    client: TestClient, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    client.post(
        "/auth/register",
        json={"email": "mig@example.com", "password": "password123", "name": "Mig"},
    )

    async def run() -> tuple[int, int, list[TrainingSession]]:
        async with db_session_factory() as db:
            user = await users_crud.get_by_email(db, "mig@example.com")
            assert user is not None
            press = {"name": "press banca", "sets": 3, "reps": 8, "weightKg": 70}
            await sessions_crud.create(db, user.id, _legacy("gym", [press]))
            await sessions_crud.create(db, user.id, _legacy("boxing", []))
            first = await migrate_legacy_strength_sessions(db)
            second = await migrate_legacy_strength_sessions(db)
            result = await db.execute(
                select(TrainingSession)
                .where(TrainingSession.user_id == user.id)
                .options(
                    selectinload(TrainingSession.exercises),
                    selectinload(TrainingSession.workout_exercises).selectinload(
                        WorkoutExercise.sets
                    ),
                )
            )
            return first, second, list(result.scalars().all())

    first, second, records = asyncio.run(run())
    assert (first, second) == (1, 0)
    by_discipline = {r.discipline: r for r in records}
    gym = by_discipline["gym"]
    assert gym.exercises == []
    assert len(gym.workout_exercises) == 1
    assert len(gym.workout_exercises[0].sets) == 3
    assert gym.volume_kg == 3 * 8 * 70
    assert gym.duration_minutes == 50
    assert "boxing" in by_discipline
