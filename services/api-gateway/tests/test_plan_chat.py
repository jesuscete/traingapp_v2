import uuid

from fastapi.testclient import TestClient

REGISTER = {"email": "plan@example.com", "password": "password123", "name": "Plan"}

SPLITS = [
    {
        "id": "push_pull_legs",
        "name": "Push / Pull / Pierna",
        "description": "Entrena 3 días de gimnasio.",
    },
    {
        "id": "fullbody_3",
        "name": "Fullbody 3 días",
        "description": "Entrena 3 días de gimnasio.",
    },
]

GENERATE = {
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


def _auth_headers(client: TestClient, email: str = REGISTER["email"]) -> dict[str, str]:
    client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Plan"},
    )
    response = client.post(
        "/auth/login", json={"email": email, "password": "password123"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _run_plan_flow(
    client: TestClient, headers: dict[str, str]
) -> tuple[str, dict]:
    start = client.post(
        "/chat/draft", json={"text": "quiero crear una rutina"}, headers=headers
    )
    assert start.status_code == 200
    start_data = start.json()
    assert start_data["mode"] == "plan"
    assert start_data["planStatus"] == "question"
    assert "deporte" in start_data["message"]
    plan_request_id = start_data["requestId"]

    client.post("/chat/draft", json={"text": "no"}, headers=headers)
    client.post("/chat/draft", json={"text": "general"}, headers=headers)
    client.post("/chat/draft", json={"text": "3"}, headers=headers)
    ready = client.post("/chat/draft", json={"text": "fullbody"}, headers=headers)
    ready_data = ready.json()
    assert ready_data["mode"] == "plan"
    assert ready_data["planStatus"] == "ready"
    assert ready_data["plan"]["name"] == "Fullbody 3 días"
    assert ready_data["requestId"] == plan_request_id
    return plan_request_id, ready_data


def test_plan_flow_via_chat(
    client: TestClient,
    _fake_redis,
    seed_catalog,
    seed_disciplines,
    monkeypatch,
) -> None:
    async def _fake_splits(sports, gym_days):
        return SPLITS

    async def _fake_generate(sports, gym_days, split_id, goal, catalog, system_prompt=None):
        return GENERATE

    monkeypatch.setattr("app.chat.plan_session.fetch_plan_splits", _fake_splits)
    monkeypatch.setattr("app.chat.plan_session.fetch_plan_generate", _fake_generate)

    headers = _auth_headers(client)
    plan_request_id, _ = _run_plan_flow(client, headers)

    confirmed = client.post(
        "/chat/plan/confirm",
        json={"planRequestId": plan_request_id},
        headers=headers,
    )
    assert confirmed.status_code == 201
    confirmed_data = confirmed.json()
    assert confirmed_data["mode"] == "plan"
    assert confirmed_data["planStatus"] == "done"
    assert "guardada" in confirmed_data["message"]

    routine = client.get("/routines/active", headers=headers)
    assert routine.status_code == 200
    assert routine.json()["name"] == "Fullbody 3 días"
    assert routine.json()["days"][0]["dayType"] == "gimnasio"


def test_plan_cancel_via_chat(
    client: TestClient,
    _fake_redis,
    seed_catalog,
    monkeypatch,
) -> None:
    async def _fake_splits(sports, gym_days):
        return SPLITS

    async def _fake_generate(sports, gym_days, split_id, goal, catalog, system_prompt=None):
        return GENERATE

    monkeypatch.setattr("app.chat.plan_session.fetch_plan_splits", _fake_splits)
    monkeypatch.setattr("app.chat.plan_session.fetch_plan_generate", _fake_generate)

    headers = _auth_headers(client, "plan-cancel@example.com")
    plan_request_id, _ = _run_plan_flow(client, headers)

    cancelled = client.post(
        "/chat/plan/cancel",
        json={"planRequestId": plan_request_id},
        headers=headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["planStatus"] == "cancelled"

    routine = client.get("/routines/active", headers=headers)
    assert routine.status_code == 200
    assert routine.json() is None


def test_plan_confirm_without_session_returns_ok(
    client: TestClient,
    _fake_redis,
    seed_catalog,
    monkeypatch,
) -> None:
    async def _fake_splits(sports, gym_days):
        return SPLITS

    async def _fake_generate(sports, gym_days, split_id, goal, catalog, system_prompt=None):
        return GENERATE

    monkeypatch.setattr("app.chat.plan_session.fetch_plan_splits", _fake_splits)
    monkeypatch.setattr("app.chat.plan_session.fetch_plan_generate", _fake_generate)

    headers = _auth_headers(client, "plan-missing@example.com")
    response = client.post(
        "/chat/plan/confirm",
        json={"planRequestId": str(uuid.uuid4())},
        headers=headers,
    )
    assert response.status_code == 201
    assert response.json()["planStatus"] == "cancelled"


def test_natural_language_starts_plan(
    client: TestClient,
    _fake_redis,
    seed_catalog,
    monkeypatch,
) -> None:
    async def _fake_splits(sports, gym_days):
        return SPLITS

    async def _fake_generate(sports, gym_days, split_id, goal, catalog, system_prompt=None):
        return GENERATE

    monkeypatch.setattr("app.chat.plan_session.fetch_plan_splits", _fake_splits)
    monkeypatch.setattr("app.chat.plan_session.fetch_plan_generate", _fake_generate)

    headers = _auth_headers(client, "plan-natural@example.com")
    response = client.post(
        "/chat/draft",
        json={"text": "Me gustaría que me recomendaras una rutina"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] == "plan"
    assert data["planStatus"] == "question"
    assert "deporte" in data["message"]


def test_ambiguous_intent_asks_then_flows(
    client: TestClient,
    _fake_redis,
    seed_catalog,
    monkeypatch,
) -> None:
    async def _fake_splits(sports, gym_days):
        return SPLITS

    async def _fake_generate(sports, gym_days, split_id, goal, catalog, system_prompt=None):
        return GENERATE

    monkeypatch.setattr("app.chat.plan_session.fetch_plan_splits", _fake_splits)
    monkeypatch.setattr("app.chat.plan_session.fetch_plan_generate", _fake_generate)

    headers = _auth_headers(client, "plan-ambiguo@example.com")
    doubt = client.post(
        "/chat/draft", json={"text": "necesito ayuda"}, headers=headers
    )
    assert doubt.status_code == 200
    doubt_data = doubt.json()
    assert doubt_data["mode"] == "plan"
    assert doubt_data["planStatus"] == "question"
    assert "¿Quieres que te recomiende un plan" in doubt_data["message"]

    ok = client.post(
        "/chat/draft", json={"text": "sí, claro"}, headers=headers
    )
    assert ok.status_code == 200
    ok_data = ok.json()
    assert ok_data["mode"] == "plan"
    assert "deporte" in ok_data["message"]


def test_plan_flow_sends_resolved_system_prompt(
    client: TestClient,
    _fake_redis,
    seed_catalog,
    seed_disciplines,
    seed_prompts,
    monkeypatch,
) -> None:
    captured: dict = {}

    async def _fake_splits(sports, gym_days):
        return SPLITS

    async def _fake_generate(sports, gym_days, split_id, goal, catalog, system_prompt=None):
        captured["system_prompt"] = system_prompt
        return GENERATE

    monkeypatch.setattr("app.chat.plan_session.fetch_plan_splits", _fake_splits)
    monkeypatch.setattr("app.chat.plan_session.fetch_plan_generate", _fake_generate)

    headers = _auth_headers(client, "plan-prompt@example.com")
    start = client.post(
        "/chat/draft", json={"text": "quiero crear una rutina"}, headers=headers
    )
    assert start.status_code == 200
    assert start.json()["planStatus"] == "question"

    client.post("/chat/draft", json={"text": "boxeo"}, headers=headers)
    client.post("/chat/draft", json={"text": "lunes y jueves"}, headers=headers)
    client.post("/chat/draft", json={"text": "1 hora"}, headers=headers)
    client.post("/chat/draft", json={"text": "general"}, headers=headers)
    client.post("/chat/draft", json={"text": "3"}, headers=headers)
    ready = client.post("/chat/draft", json={"text": "fullbody"}, headers=headers)
    assert ready.status_code == 200
    assert ready.json()["planStatus"] == "ready"
    assert ready.json()["plan"]["name"] == "Fullbody 3 días - Boxeo"

    system_prompt = captured.get("system_prompt")
    assert system_prompt is not None
    assert "Potencia / explosividad" in system_prompt
    assert "{perfil}" not in system_prompt
    assert "{deportes}" in system_prompt
    assert "{catalogo_ejercicios}" in system_prompt
