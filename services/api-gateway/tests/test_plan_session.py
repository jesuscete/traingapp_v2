import asyncio
import uuid

from app.chat.plan_session import (
    cancel_plan,
    confirm_plan,
    is_plan_start,
    parse_day_count,
    parse_duration_answer,
    parse_gym_days_answer,
    parse_gym_purpose_answer,
    parse_split_choice,
    parse_sports_answer,
    parse_weekdays_answer,
    process_plan_message,
    spread_days,
)
from app.crud import routine as routine_crud

SPLITS = [
    {
        "id": "fullbody_2",
        "name": "Fullbody 2 días",
        "description": "Entrena 2 días de gimnasio.",
    },
    {
        "id": "torso_pierna",
        "name": "Torso / Pierna (2 días)",
        "description": "Entrena 2 días de gimnasio.",
    },
]

GYM_GENERATE = {
    "name": "Plan semanal",
    "days": [
        {
            "dayOfWeek": 1,
            "dayType": "gimnasio",
            "label": "Gimnasio 1",
            "exercises": [
                {
                    "name": "press banca",
                    "sets": [
                        {
                            "targetRepsMin": 8,
                            "targetRepsMax": 12,
                            "targetRestSeconds": 90,
                        }
                    ],
                }
            ],
        },
        {"dayOfWeek": 2, "dayType": "descanso", "label": "Descanso"},
    ],
}

SPORT_GENERATE = {
    "name": "Plan boxeo",
    "days": [
        {
            "dayOfWeek": 1,
            "dayType": "deporte",
            "label": "boxeo",
            "discipline": "boxing",
            "durationMin": 90,
        },
        {"dayOfWeek": 2, "dayType": "descanso", "label": "Descanso"},
    ],
}


def test_is_plan_start() -> None:
    assert is_plan_start("quiero crear una rutina")
    assert is_plan_start("recomiéndame un plan")
    assert is_plan_start("recomiendame un plan")
    assert is_plan_start("crea mi rutina semanal")
    assert is_plan_start("Me gustaría que me recomendaras una rutina")
    assert not is_plan_start("5x5 press banca 80kg")
    assert not is_plan_start("necesito ayuda")
    assert not is_plan_start("hola, ¿cómo estás?")


def test_parse_sports_answer() -> None:
    assert parse_sports_answer("no practico deportes") == []
    assert parse_sports_answer("hago boxeo y salgo a correr") == [
        "boxeo",
        "correr",
    ]
    assert parse_sports_answer("boxeo, running y tenis") == [
        "boxeo",
        "running",
        "tenis",
    ]
    assert parse_sports_answer("no se que responder") == []
    assert parse_sports_answer("") is None
    assert parse_sports_answer("hago boxeo y corro") == ["boxeo", "correr"]


def test_parse_day_count() -> None:
    assert parse_day_count("2") == 2
    assert parse_day_count("dos") == 2
    assert parse_day_count("tres días") == 3
    assert parse_day_count("7") == 7
    assert parse_day_count("8") is None
    assert parse_day_count("no se") is None


def test_spread_days() -> None:
    assert spread_days(1) == [3]
    assert spread_days(2) == [1, 7]
    assert spread_days(3) == [1, 4, 7]
    assert spread_days(7) == [1, 2, 3, 4, 5, 6, 7]


def test_parse_duration_answer() -> None:
    assert parse_duration_answer("90 minutos") == 90
    assert parse_duration_answer("1.5 h") == 90
    assert parse_duration_answer("2 horas") == 120
    assert parse_duration_answer("no se") is None


def test_parse_gym_days_answer() -> None:
    assert parse_gym_days_answer("3") == 3
    assert parse_gym_days_answer("no voy al gym") == 0
    assert parse_gym_days_answer("9") is None


def test_parse_weekdays_answer() -> None:
    assert parse_weekdays_answer("lunes y jueves") == [1, 4]
    assert parse_weekdays_answer("1 y 4") == [1, 4]
    assert parse_weekdays_answer("entre semana") == [1, 2, 3, 4, 5]
    assert parse_weekdays_answer("fines de semana") == [6, 7]
    assert parse_weekdays_answer("miércoles") == [3]
    assert parse_weekdays_answer("no se") is None


def test_parse_gym_purpose_answer() -> None:
    from app.chat.plan_session import SportAnswer

    sports = [SportAnswer(name="boxeo"), SportAnswer(name="correr")]
    assert parse_gym_purpose_answer("para mejorar en boxeo", sports) == "boxeo"
    assert parse_gym_purpose_answer("para mejorar en correr", sports) == "correr"
    assert parse_gym_purpose_answer("entrenar de forma general", sports) == "general"
    assert parse_gym_purpose_answer("gimnasio", sports) == "general"
    assert parse_gym_purpose_answer("no, gracias", sports) == "none"


def test_parse_split_choice() -> None:
    assert parse_split_choice("fullbody") == "fullbody"
    assert parse_split_choice("cuerpo completo") == "fullbody"
    assert parse_split_choice("empuje-tirón") == "push_pull"
    assert parse_split_choice("torso-pierna") == "torso_pierna"
    assert parse_split_choice("upper/lower") == "upper_lower"
    assert parse_split_choice("weider") == "upper_lower"
    assert parse_split_choice("me da igual") == "any"
    assert parse_split_choice("no se") is None


def test_full_flow_without_sports(
    _fake_redis, db_session_factory, seed_catalog, monkeypatch
) -> None:
    async def _fake_splits(sports, gym_days):
        return SPLITS

    async def _fake_generate(sports, gym_days, split_id, goal, catalog):
        return GYM_GENERATE

    monkeypatch.setattr("app.chat.plan_session.fetch_plan_splits", _fake_splits)
    monkeypatch.setattr("app.chat.plan_session.fetch_plan_generate", _fake_generate)

    user_id = uuid.uuid4()

    async def run() -> None:
        async with db_session_factory() as session:
            start = await process_plan_message(
                _fake_redis, user_id, session, "quiero crear una rutina"
            )
            assert start.status == "question"
            assert "deporte" in start.message

            await process_plan_message(_fake_redis, user_id, session, "no")
            await process_plan_message(_fake_redis, user_id, session, "general")
            await process_plan_message(_fake_redis, user_id, session, "3")
            ready = await process_plan_message(
                _fake_redis, user_id, session, "fullbody"
            )
            assert ready.status == "ready"
            assert ready.plan is not None
            assert ready.plan.name == "Plan semanal"
            assert ready.request_id == start.request_id

            confirmed = await confirm_plan(
                _fake_redis, user_id, session, ready.request_id
            )
            assert confirmed.status == "done"
            assert confirmed.cleared

            routine = await routine_crud.get_active_routine(session, user_id)
            assert routine is not None
            assert routine.name == "Plan semanal"
            assert routine.days[0].day_type == "gimnasio"
            assert routine.days[0].exercises[0].exercise_id is not None

    asyncio.run(run())


def test_flow_with_sport_resolves_discipline(
    _fake_redis, db_session_factory, seed_catalog, seed_disciplines, monkeypatch
) -> None:
    async def _fake_generate(sports, gym_days, split_id, goal, catalog):
        return SPORT_GENERATE

    monkeypatch.setattr("app.chat.plan_session.fetch_plan_generate", _fake_generate)

    user_id = uuid.uuid4()

    async def run() -> None:
        async with db_session_factory() as session:
            await process_plan_message(
                _fake_redis, user_id, session, "quiero crear una rutina"
            )
            await process_plan_message(_fake_redis, user_id, session, "boxeo")
            await process_plan_message(_fake_redis, user_id, session, "lunes y jueves")
            await process_plan_message(_fake_redis, user_id, session, "90 minutos")
            ready = await process_plan_message(_fake_redis, user_id, session, "no")
            assert ready.status == "ready"
            assert ready.plan is not None
            sport_day = ready.plan.days[0]
            assert sport_day.day_type == "deporte"
            assert sport_day.discipline_id is not None
            assert sport_day.duration_min == 90

            confirmed = await confirm_plan(
                _fake_redis, user_id, session, ready.request_id
            )
            assert confirmed.status == "done"

            routine = await routine_crud.get_active_routine(session, user_id)
            assert routine is not None
            assert routine.days[0].day_type == "deporte"
            assert routine.days[0].discipline_id is not None

    asyncio.run(run())


def test_cancel_plan_at_summary(
    _fake_redis, db_session_factory, seed_catalog, monkeypatch
) -> None:
    async def _fake_splits(sports, gym_days):
        return SPLITS

    async def _fake_generate(sports, gym_days, split_id, goal, catalog):
        return GYM_GENERATE

    monkeypatch.setattr("app.chat.plan_session.fetch_plan_splits", _fake_splits)
    monkeypatch.setattr("app.chat.plan_session.fetch_plan_generate", _fake_generate)

    user_id = uuid.uuid4()

    async def run() -> None:
        async with db_session_factory() as session:
            await process_plan_message(
                _fake_redis, user_id, session, "quiero crear una rutina"
            )
            await process_plan_message(_fake_redis, user_id, session, "no")
            await process_plan_message(_fake_redis, user_id, session, "general")
            await process_plan_message(_fake_redis, user_id, session, "3")
            ready = await process_plan_message(
                _fake_redis, user_id, session, "fullbody"
            )
            assert ready.status == "ready"

            cancelled = await cancel_plan(_fake_redis, user_id, ready.request_id)
            assert cancelled.status == "cancelled"
            assert cancelled.cleared

            routine = await routine_crud.get_active_routine(session, user_id)
            assert routine is None

    asyncio.run(run())


def test_ambiguous_intent_asks_confirmation_then_flow(
    _fake_redis, db_session_factory, seed_catalog, monkeypatch
) -> None:
    async def _fake_splits(sports, gym_days):
        return SPLITS

    async def _fake_generate(sports, gym_days, split_id, goal, catalog):
        return GYM_GENERATE

    monkeypatch.setattr("app.chat.plan_session.fetch_plan_splits", _fake_splits)
    monkeypatch.setattr("app.chat.plan_session.fetch_plan_generate", _fake_generate)

    user_id = uuid.uuid4()

    async def run() -> None:
        async with db_session_factory() as session:
            confirm_step = await process_plan_message(
                _fake_redis, user_id, session, "necesito ayuda"
            )
            assert confirm_step.status == "question"
            assert "¿Quieres que te recomiende un plan" in confirm_step.message

            start = await process_plan_message(
                _fake_redis, user_id, session, "sí, claro"
            )
            assert start.status == "question"
            assert "deporte" in start.message

            await process_plan_message(_fake_redis, user_id, session, "no")
            await process_plan_message(_fake_redis, user_id, session, "general")
            await process_plan_message(_fake_redis, user_id, session, "3")
            ready = await process_plan_message(
                _fake_redis, user_id, session, "fullbody"
            )
            assert ready.status == "ready"
            assert ready.plan is not None

            routine = await routine_crud.get_active_routine(session, user_id)
            assert routine is None

    asyncio.run(run())


def test_ambiguous_intent_cancel(
    _fake_redis, db_session_factory, monkeypatch
) -> None:
    user_id = uuid.uuid4()

    async def run() -> None:
        async with db_session_factory() as session:
            confirm_step = await process_plan_message(
                _fake_redis, user_id, session, "¿me recomiendas algo?"
            )
            assert confirm_step.status == "question"
            assert confirm_step.request_id is not None

            cancelled = await process_plan_message(
                _fake_redis, user_id, session, "no"
            )
            assert cancelled.status == "cancelled"
            assert cancelled.cleared

    asyncio.run(run())


def test_confirm_rejects_wrong_request_id(
    _fake_redis, db_session_factory, seed_catalog, monkeypatch
) -> None:
    async def _fake_splits(sports, gym_days):
        return SPLITS

    async def _fake_generate(sports, gym_days, split_id, goal, catalog):
        return GYM_GENERATE

    monkeypatch.setattr("app.chat.plan_session.fetch_plan_splits", _fake_splits)
    monkeypatch.setattr("app.chat.plan_session.fetch_plan_generate", _fake_generate)

    user_id = uuid.uuid4()

    async def run() -> None:
        async with db_session_factory() as session:
            await process_plan_message(
                _fake_redis, user_id, session, "quiero crear una rutina"
            )
            await process_plan_message(_fake_redis, user_id, session, "no")
            await process_plan_message(_fake_redis, user_id, session, "general")
            await process_plan_message(_fake_redis, user_id, session, "3")
            ready = await process_plan_message(
                _fake_redis, user_id, session, "fullbody"
            )
            assert ready.status == "ready"

            result = await confirm_plan(_fake_redis, user_id, session, uuid.uuid4())
            assert result.status == "cancelled"
            routine = await routine_crud.get_active_routine(session, user_id)
            assert routine is None

    asyncio.run(run())
