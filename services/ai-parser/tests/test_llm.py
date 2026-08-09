import asyncio

from app.llm.base import LLMProvider
from app.parsing.llm import parse_with_llm
from app.parsing.service import parse_workout

_GOOD_JSON = (
    '{"discipline":"gym","performedAt":"2026-08-08T18:30:00Z",'
    '"durationMinutes":60,"suggestedRpe":8,'
    '"exercises":[{"name":"press banca","sets":4,"reps":7,'
    '"perSetReps":[8,7,7,5],"weightKg":80}],'
    '"confidence":0.95,"unresolved":[]}'
)


class FakeProvider(LLMProvider):
    name = "fake"

    def __init__(self, content: str = _GOOD_JSON, *, error: bool = False) -> None:
        self._content = content
        self._error = error

    async def complete(self, system: str, user: str) -> str:
        if self._error:
            raise RuntimeError("provider boom")
        return self._content


def test_parse_with_llm_json() -> None:
    result = asyncio.run(parse_with_llm(FakeProvider(), "5x5 press banca 80kg"))
    assert result.discipline == "gym"
    assert result.durationMinutes == 60
    assert result.suggestedRpe == 8.0
    assert result.confidence == 0.95
    exercise = result.exercises[0]
    assert exercise.per_set_reps == [8, 7, 7, 5]
    assert (exercise.sets, exercise.reps, exercise.weight_kg) == (4, 7, 80.0)


def test_parse_with_llm_fenced_json() -> None:
    fenced = "```json\n" + _GOOD_JSON + "\n```"
    result = asyncio.run(parse_with_llm(FakeProvider(fenced), "press banca"))
    assert result.discipline == "gym"


def test_parse_with_llm_invalid_discipline_falls_to_other() -> None:
    content = '{"discipline":"crossfit","exercises":[],"confidence":0.5,"unresolved":[]}'
    result = asyncio.run(parse_with_llm(FakeProvider(content), "x"))
    assert result.discipline == "other"


def test_parse_workout_falls_back_to_stub(monkeypatch) -> None:
    from app.llm import factory

    monkeypatch.setattr(factory, "get_provider", lambda: FakeProvider(error=True))
    result = asyncio.run(parse_workout("5x5 press banca 80kg"))
    assert result.discipline == "gym"
    assert result.exercises[0].reps == 5


def test_parse_workout_no_provider_uses_stub(monkeypatch) -> None:
    from app.llm import factory

    monkeypatch.setattr(factory, "get_provider", lambda: None)
    result = asyncio.run(parse_workout("carrera de 45 min"))
    assert result.discipline == "running"
    assert result.durationMinutes == 45
