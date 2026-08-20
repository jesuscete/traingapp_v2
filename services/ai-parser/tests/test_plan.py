import asyncio

from app.llm.base import LLMProvider
from app.parsing.plan import generate_plan_with_llm, suggest_splits_with_llm
from app.parsing.plan_service import generate_plan, suggest_splits
from app.parsing.plan_stub import (
    _is_explosive,
    generate_plan_stub,
    suggest_splits_stub,
)
from app.schemas.plan import (
    PlanGenerateIn,
    PlanResponse,
    PlanSetTarget,
    SportIn,
)

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
    "Press empujadora",
    "Landmine press",
    "Cargada de potencia",
    "Balanceo con kettlebell",
    "Saltos al cajón",
    "Saltos verticales",
    "Lanzamiento de balón medicinal",
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


def test_generate_plan_stub_name_split_and_sport() -> None:
    result = generate_plan_stub(_SPORTS, 3, "push_pull_legs", "performance", _CATALOG)
    assert result.name == "Push / Pull / Pierna - Boxeo"


def test_generate_plan_stub_name_split_only() -> None:
    result = generate_plan_stub([], 3, "push_pull_legs", "aesthetic", _CATALOG)
    assert result.name == "Push / Pull / Pierna"


def test_generate_plan_stub_name_sport_only() -> None:
    result = generate_plan_stub(_SPORTS, 0, None, "performance", _CATALOG)
    assert result.name == "Boxeo"


def test_generate_plan_stub_three_sets() -> None:
    result = generate_plan_stub(_SPORTS, 3, "push_pull_legs", "performance", _CATALOG)
    gym_days = [day for day in result.days if day.day_type == "gimnasio"]
    assert gym_days
    for day in gym_days:
        assert day.exercises
        for exercise in day.exercises:
            assert len(exercise.sets) == 3


def test_generate_plan_stub_protocol_by_goal() -> None:
    performance = generate_plan_stub(
        _SPORTS, 3, "push_pull_legs", "performance", _CATALOG
    )
    aesthetic = generate_plan_stub(_SPORTS, 3, "push_pull_legs", "aesthetic", _CATALOG)

    def first_main(plan: PlanResponse) -> PlanSetTarget:
        for day in plan.days:
            if day.day_type != "gimnasio":
                continue
            for exercise in day.exercises:
                if _is_explosive(exercise.name):
                    continue
                return exercise.sets[0]
        raise AssertionError("no main exercise")

    perf_main = first_main(performance)
    aest_main = first_main(aesthetic)
    assert (perf_main.target_reps_min, perf_main.target_reps_max) == (6, 10)
    assert (aest_main.target_reps_min, aest_main.target_reps_max) == (10, 15)


def test_generate_plan_stub_adds_explosive_for_power() -> None:
    result = generate_plan_stub(_SPORTS, 3, "push_pull_legs", "performance", _CATALOG)
    gym_days = [day for day in result.days if day.day_type == "gimnasio"]
    assert gym_days
    for day in gym_days:
        assert day.exercises
        assert any(_is_explosive(exercise.name) for exercise in day.exercises)


def test_generate_plan_stub_no_explosive_aesthetic() -> None:
    result = generate_plan_stub(_SPORTS, 3, "push_pull_legs", "aesthetic", _CATALOG)
    for day in result.days:
        for exercise in day.exercises:
            assert not _is_explosive(exercise.name)


def test_generate_plan_stub_no_explosive_without_sports() -> None:
    result = generate_plan_stub([], 3, "push_pull_legs", "performance", _CATALOG)
    for day in result.days:
        for exercise in day.exercises:
            assert not _is_explosive(exercise.name)


def test_generate_plan_stub_caps_six_exercises_per_day() -> None:
    result = generate_plan_stub(_SPORTS, 3, "push_pull_legs", "performance", _CATALOG)
    for day in result.days:
        assert len(day.exercises) <= 6


def test_generate_plan_stub_varies_exercises_across_days() -> None:
    result = generate_plan_stub(
        _SPORTS, 4, "torso_pierna_2x", "performance", _CATALOG
    )
    gym_days = [day for day in result.days if day.day_type == "gimnasio"]
    assert len(gym_days) >= 2
    exercise_sets = [
        tuple(exercise.name for exercise in day.exercises) for day in gym_days
    ]
    assert len(set(exercise_sets)) == len(exercise_sets)
    for day in gym_days:
        names = [exercise.name for exercise in day.exercises]
        assert len(set(names)) == len(names)


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


def test_generate_plan_with_llm_profile_prompt_with_literal_braces() -> None:
    class CapturingProvider(FakeProvider):
        def __init__(self) -> None:
            super().__init__()
            self.seen: str | None = None

        async def complete(self, system: str, user: str) -> str:
            self.seen = system
            return self._content

    profile = (
        "Eres un entrenador de explosividad. Objetivo: {objetivo}. "
        'Devuelve JSON: {"dayOfWeek": 1, "dayType": "gimnasio", '
        '"exercises": [{"name": "Saltos", "sets": [{...}]}]}. '
        "Catalogo: {catalogo_ejercicios}"
    )
    provider = CapturingProvider()
    result = asyncio.run(
        generate_plan_with_llm(
            provider, _SPORTS, 3, None, "performance", _CATALOG,
            system_prompt=profile,
        )
    )
    assert result.name == "Plan boxeo + gym"
    assert provider.seen is not None
    assert "{objetivo}" not in provider.seen
    assert "{catalogo_ejercicios}" not in provider.seen
    assert "performance" in provider.seen
    assert "Press banca" in provider.seen


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


def test_generate_plan_empty_llm_plan_falls_back_to_stub(monkeypatch) -> None:
    from app.llm import factory

    monkeypatch.setattr(
        factory, "get_provider", lambda: FakeProvider('{"name":"x","days":[]}')
    )
    body = PlanGenerateIn(
        sports=_SPORTS,
        gym_days=3,
        split_id="push_pull_legs",
        goal="performance",
        catalog=_CATALOG,
    )
    result = asyncio.run(generate_plan(body))
    assert result.days
    gym_days = [day for day in result.days if day.day_type == "gimnasio"]
    assert gym_days
    assert all(day.exercises for day in gym_days)
    assert all(
        any(_is_explosive(exercise.name) for exercise in day.exercises)
        for day in gym_days
    )


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
