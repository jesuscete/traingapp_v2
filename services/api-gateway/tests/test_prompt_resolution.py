import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.crud.prompt import resolve_training_prompt
from app.models import TrainingPrompt


def _resolve(
    db_session_factory: async_sessionmaker[AsyncSession], discipline_names: list[str]
) -> TrainingPrompt | None:
    async def run() -> TrainingPrompt | None:
        async with db_session_factory() as session:
            return await resolve_training_prompt(session, discipline_names)

    return asyncio.run(run())


def test_boxing_resolves_to_explosividad(
    seed_disciplines, seed_prompts, db_session_factory
) -> None:
    prompt = _resolve(db_session_factory, ["boxing"])
    assert prompt is not None
    assert prompt.code == "explosividad"
    assert not prompt.is_default


def test_running_resolves_to_resistencia(
    seed_disciplines, seed_prompts, db_session_factory
) -> None:
    prompt = _resolve(db_session_factory, ["running"])
    assert prompt is not None
    assert prompt.code == "resistencia"


def test_unknown_discipline_falls_back_to_balanced(
    seed_disciplines, seed_prompts, db_session_factory
) -> None:
    prompt = _resolve(db_session_factory, ["cricket"])
    assert prompt is not None
    assert prompt.code == "balanced"
    assert prompt.is_default


def test_empty_disciplines_uses_default(
    seed_disciplines, seed_prompts, db_session_factory
) -> None:
    prompt = _resolve(db_session_factory, [])
    assert prompt is not None
    assert prompt.code == "balanced"


def test_no_prompt_rows_returns_none(
    seed_disciplines, db_session_factory
) -> None:
    assert _resolve(db_session_factory, ["boxing"]) is None


def test_first_sport_with_profile_wins(
    seed_disciplines, seed_prompts, db_session_factory
) -> None:
    running_first = _resolve(db_session_factory, ["running", "boxing"])
    boxing_first = _resolve(db_session_factory, ["boxing", "running"])
    assert running_first is not None
    assert boxing_first is not None
    assert running_first.code == "resistencia"
    assert boxing_first.code == "explosividad"
