import asyncio

from app.llm.base import LLMProvider
from app.parsing.plan import generate_plan_with_llm, suggest_splits_with_llm
from app.parsing.plan_service import generate_plan, suggest_splits
from app.parsing.plan_stub import generate_plan_stub, suggest_splits_stub
from app.schemas.plan import PlanGenerateIn, SportIn

_CATALOG = [
    "Press banca",
    "Press militar",
    "Remo con barra",
    "Dominadas",
    "Sentadilla",
    "Peso muerto rumano",
    "Curl bíceps",
    "Push down",
    "Plancha",
    "Russian twist",
]

_SPORTS = [SportIn(name="Boxeo", days=[1, 3], duration_min=60)]

_GOOD_PLAN_JSON = (
    '{"name":"Plan boxeo + gym","days":['
    '{"dayOfWeek":1,"dayType":"deporte","label":"Boxeo","discipline":"boxing","durationMin":60},'
    '{"dayOfWeek":2,"dayType":"gimnasio","label":"Gimnasio 1",'
    '"exercises":[{"name":"Press banca","sets":[{"targetRepsMin":8,"targetRepsMax":12}]},'
    '{"name":"Remo con barra","sets":[{"targetRepsMin":8,"targetRepsMax":12}]}]},'
    '{"dayOfWeek":3,"dayType":"deporte","label":"Boxeo","discipline":"boxing","durationMin":60},'
    '{"dayOfWeek":4,"dayType":"descanso"}]}'
)

_GOOD_SPLITS_JSON = (
    '{"options":['
    '{"id":"torso_pierna_2x","name":"Torso/Pierna x2",'
    '"description":"Evita cargar pierna antes de boxeo"},'
    '{"id":"fullbody_4","name":"Fullbody 4 días","description":"Distribución equilibrada"}]}'
)


class FakeProvider(LLMProvider):
    name = "fake"

    def __init__(self, content: str = _GOOD_PLAN_JSON, *, error: bool = False) -> None:
        self._content = content
        self._error = error

    async def complete(self, system: str, user: str) -> str:
        if self._error:
            raise RuntimeError("provider boom")
        return self._content


def test_suggest_splits_stub_by_frequency() -> None:
    result = suggest_splits_stub([], 2)
    assert len(result.options) == 2
    assert all(option.id and option.name and option.description for option in result.options)
    result_four = suggest_splits_stub([], 4)
    assert result_four.options[0].id == "torso_pierna_2x"


def test_suggest_splits_stub_zero_gym() -> None:
    assert suggest_splits_stub([], 0).options == []


def test_generate_plan_stub_reserves_sport_days() -> None:
    result = generate_plan_stub(_SPORTS, 3, "push_pull_legs", "performance", _CATALOG)
    assert len(result.days) == 7
    sport_days = [day for day in result.days if day.day_type == "deporte"]
    assert [day.day_of_week for day in sport_days] == [1, 3]
    assert all(day.discipline == "boxeo" for day in sport_days)
    assert all(day.duration_min == 60 for day in sport_days)
    assert all(day.exercises == [] for day in sport_days)


def test_generate_plan_stub_uses_only_catalog() -> None:
    result = generate_plan_stub(_SPORTS, 3, "push_pull_legs", "aesthetic", _CATALOG)
    catalog_set = {name.lower() for name in _CATALOG}
    for day in result.days:
        for exercise in day.exercises:
            assert exercise.name.lower() in catalog_set
        assert len(day.exercises) <= 6


def test_generate_plan_stub_caps_gym_to_free_days() -> None:
    result = generate_plan_stub(_SPORTS, 6, "push_pull_legs_2x", "performance", _CATALOG)
    gym_days = [day for day in result.days if day.day_type == "gimnasio"]
    assert len(gym_days) <= 5


def test_generate_plan_with_llm_json() -> None:
    result = asyncio.run(
        generate_plan_with_llm(
            FakeProvider(), _SPORTS, 3, "push_pull_legs", "performance", _CATALOG
        )
    )
    assert result.name == "Plan boxeo + gym"
    deporte = result.days[0]
    assert deporte.day_type == "deporte"
    assert deporte.discipline == "boxing"
    assert deporte.duration_min == 60
    gym = result.days[1]
    assert gym.day_type == "gimnasio"
    assert [exercise.name for exercise in gym.exercises] == [
        "Press banca",
        "Remo con barra",
    ]
    assert gym.exercises[0].sets[0].target_reps_max == 12


def test_generate_plan_with_llm_fenced_json() -> None:
    fenced = "```json\n" + _GOOD_PLAN_JSON + "\n```"
    result = asyncio.run(
        generate_plan_with_llm(FakeProvider(fenced), _SPORTS, 3, None, "aesthetic", _CATALOG)
    )
    assert result.days[1].day_type == "gimnasio"


def test_generate_plan_with_llm_drops_non_catalog_exercises() -> None:
    content = (
        '{"name":"x","days":[{"dayOfWeek":2,"dayType":"gimnasio",'
        '"exercises":[{"name":"Press banca","sets":[]},'
        '{"name":"Invented raise","sets":[]}]}]}'
    )
    result = asyncio.run(
        generate_plan_with_llm(FakeProvider(content), [], 1, None, "aesthetic", _CATALOG)
    )
    assert [exercise.name for exercise in result.days[0].exercises] == ["Press banca"]


def test_suggest_splits_with_llm_json() -> None:
    result = asyncio.run(
        suggest_splits_with_llm(FakeProvider(_GOOD_SPLITS_JSON), _SPORTS, 4)
    )
    assert len(result.options) == 2
    assert result.options[0].id == "torso_pierna_2x"
    assert "boxeo" in result.options[0].description.lower()


def test_generate_plan_falls_back_to_stub(monkeypatch) -> None:
    from app.llm import factory

    monkeypatch.setattr(factory, "get_provider", lambda: FakeProvider(error=True))
    body = PlanGenerateIn(
        sports=_SPORTS,
        gym_days=3,
        split_id="push_pull_legs",
        goal="performance",
        catalog=_CATALOG,
    )
    result = asyncio.run(generate_plan(body))
    assert result.days
    assert any(day.day_type == "deporte" for day in result.days)


def test_generate_plan_no_provider_uses_stub(monkeypatch) -> None:
    from app.llm import factory

    monkeypatch.setattr(factory, "get_provider", lambda: None)
    body = PlanGenerateIn(
        sports=_SPORTS,
        gym_days=3,
        split_id="push_pull_legs",
        goal="aesthetic",
        catalog=_CATALOG,
    )
    result = asyncio.run(generate_plan(body))
    assert result.days


def test_suggest_splits_no_provider_uses_stub(monkeypatch) -> None:
    from app.llm import factory

    monkeypatch.setattr(factory, "get_provider", lambda: None)
    result = asyncio.run(suggest_splits([SportIn(name="Boxeo", days=[1], duration_min=60)], 4))
    assert result.options
