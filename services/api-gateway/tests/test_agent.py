import asyncio
import json
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient


def _headers(client: TestClient, email: str) -> dict[str, str]:
    body = {"email": email, "password": "password123", "name": "Boxer"}
    token = client.post("/auth/register", json=body).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class ScriptedAgent:
    """Simula ai-parser /agent/step devolviendo pasos en orden y registrando lo recibido."""

    def __init__(self, *steps: dict[str, Any]) -> None:
        self.steps = list(steps)
        self.payloads: list[dict[str, Any]] = []

    async def __call__(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.payloads.append(payload)
        return self.steps.pop(0)


def _reply(message: str) -> dict[str, Any]:
    return {"source": "llm", "action": "responder", "message": message, "arguments": {}}


def _tool(name: str, **arguments: Any) -> dict[str, Any]:
    return {"source": "llm", "action": "herramienta", "tool": name, "arguments": arguments}


@pytest.fixture
def ids(client: TestClient, seed_catalog) -> dict[str, str]:
    headers = _headers(client, "catalog-reader@example.com")
    items = client.get("/catalog/exercises", headers=headers).json()
    return {e["normalizedName"]: e["id"] for e in items}


def _routine(client: TestClient, headers: dict[str, str], exercise_id: str) -> dict[str, Any]:
    body = {
        "name": "Boxeo",
        "days": [
            {
                "dayOfWeek": 1,
                "dayType": "gimnasio",
                "exercises": [
                    {
                        "exerciseId": exercise_id,
                        "orderIndex": 0,
                        "sets": [{"setNumber": 1, "targetRepsMin": 8, "targetRepsMax": 10}],
                    }
                ],
            }
        ],
    }
    response = client.post("/routines", json=body, headers=headers)
    assert response.status_code == 201
    return response.json()


def test_agent_reads_data_with_tools_and_keeps_memory(
    client: TestClient, ids: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _headers(client, "agent-read@example.com")
    _routine(client, headers, ids["press banca"])
    script = ScriptedAgent(
        _tool("ver_rutina"), _reply("Tienes press banca el lunes."), _reply("De nada.")
    )
    monkeypatch.setattr("app.core.agent.fetch_agent_step", script)

    first = client.post("/agent/message", json={"text": "¿qué tengo el lunes?"}, headers=headers)
    assert first.status_code == 200, first.text
    data = first.json()
    assert data == {
        "source": "llm",
        "reply": "Tienes press banca el lunes.",
        "actions": [],
        "toolsUsed": ["ver_rutina"],
    }
    tool_message = script.payloads[1]["messages"][-1]
    assert (
        tool_message["role"] == "herramienta" and "routine_exercise_id" in tool_message["content"]
    )
    assert {t["name"] for t in script.payloads[0]["tools"]} >= {"ver_fatiga", "registrar_entreno"}

    client.post("/agent/message", json={"text": "gracias"}, headers=headers)
    remembered = [m["content"] for m in script.payloads[2]["messages"]]
    assert "¿qué tengo el lunes?" in remembered and "Tienes press banca el lunes." in remembered


def test_ver_rutina_filters_day_and_numbers_gym_sessions(
    client: TestClient, ids: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _headers(client, "agent-day@example.com")
    _routine(client, headers, ids["press banca"])
    script = ScriptedAgent(_tool("ver_rutina", dia=2), _tool("ver_rutina", dia=1), _reply("Ok."))
    monkeypatch.setattr("app.core.agent.fetch_agent_step", script)

    client.post("/agent/message", json={"text": "dame el día 1"}, headers=headers)
    empty = json.loads(script.payloads[1]["messages"][-1]["content"])
    assert empty["dias"] == []
    monday = json.loads(script.payloads[2]["messages"][-1]["content"])
    assert [d["dia"] for d in monday["dias"]] == [1]
    assert monday["dias"][0]["sesion_gimnasio"] == 1


def test_oversized_tool_result_is_marked_truncated(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import agent as agent_service
    from app.services.agent_tools import TOOLS, Tool, ToolResult

    async def big(_ctx: object, _args: dict[str, object]) -> ToolResult:
        return ToolResult({"x": "a" * (agent_service.MAX_TOOL_CONTENT + 10)})

    monkeypatch.setitem(TOOLS, "ver_rutina", Tool("ver_rutina", "", big))
    content, _ = asyncio.run(agent_service._run_tool(None, "ver_rutina", {}))  # type: ignore[arg-type]
    assert content.endswith("]") and "TRUNCADO" in content


def test_agent_proposal_requires_confirmation(
    client: TestClient, ids: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _headers(client, "agent-write@example.com")
    routine = _routine(client, headers, ids["press banca"])
    script = ScriptedAgent(
        _tool(
            "anadir_a_rutina",
            dia=1,
            exercise_id=ids["russian twist"],
            series=3,
            reps_min=12,
            reps_max=15,
        ),
        _reply("Te propongo añadir giro ruso el lunes. Confírmalo."),
    )
    monkeypatch.setattr("app.core.agent.fetch_agent_step", script)

    data = client.post("/agent/message", json={"text": "añade core"}, headers=headers).json()
    assert len(data["actions"]) == 1
    action = data["actions"][0]
    assert action["type"] == "add_exercise" and "lunes" in action["summary"]
    unchanged = client.get("/routines/active", headers=headers).json()
    assert len(unchanged["days"][0]["exercises"]) == 1  # nada se aplica sin confirmar

    stranger = _headers(client, "agent-stranger@example.com")
    url = f"/agent/actions/{action['id']}/confirm"
    assert client.post(url, headers=stranger).status_code == 404
    confirmed = client.post(url, headers=headers)
    assert confirmed.status_code == 200, confirmed.text
    exercises = client.get("/routines/active", headers=headers).json()["days"][0]["exercises"]
    assert exercises[-1]["exerciseId"] == ids["russian twist"] and len(exercises[-1]["sets"]) == 3
    assert client.post(url, headers=headers).status_code == 404
    assert routine["id"] == client.get("/routines/active", headers=headers).json()["id"]


def test_agent_logs_workout_as_draft(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    headers = _headers(client, "agent-log@example.com")

    async def fake_draft(text: str) -> dict[str, Any]:
        return {
            "rawText": text,
            "discipline": "boxing",
            "performedAt": "2026-11-10T18:00:00Z",
            "durationMinutes": 60,
            "exercises": [],
            "confidence": 0.9,
            "unresolved": [],
        }

    monkeypatch.setattr("app.services.agent_tools.fetch_draft", fake_draft)
    script = ScriptedAgent(
        _tool("registrar_entreno", texto="1h de boxeo"), _reply("Te lo dejo listo para guardar.")
    )
    monkeypatch.setattr("app.core.agent.fetch_agent_step", script)

    data = client.post("/agent/message", json={"text": "hice 1h de boxeo"}, headers=headers).json()
    action = data["actions"][0]
    assert action["type"] == "save_workout" and action["requestId"]
    saved = client.post("/chat/confirm", json={"requestId": action["requestId"]}, headers=headers)
    assert saved.status_code == 201 and saved.json()["discipline"] == "boxing"


def test_agent_bad_arguments_and_ai_down(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _headers(client, "agent-errors@example.com")
    script = ScriptedAgent(_tool("explicar_fatiga", grupo="pies"), _reply("¿Qué músculo?"))
    monkeypatch.setattr("app.core.agent.fetch_agent_step", script)
    data = client.post("/agent/message", json={"text": "¿y los pies?"}, headers=headers).json()
    assert "Grupo desconocido" in script.payloads[1]["messages"][-1]["content"]
    assert data["reply"] == "¿Qué músculo?"

    async def down(payload: dict[str, Any]) -> dict[str, Any]:
        raise httpx.ConnectError("caído")

    monkeypatch.setattr("app.core.agent.fetch_agent_step", down)
    fallback = client.post("/agent/message", json={"text": "hola"}, headers=headers)
    assert fallback.status_code == 200
    assert fallback.json()["source"] == "fallback"


def test_agent_stops_after_max_tool_steps(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = _headers(client, "agent-loop@example.com")
    script = ScriptedAgent(*[_tool("ver_fatiga")] * 4, _reply("Resumen final."))
    monkeypatch.setattr("app.core.agent.fetch_agent_step", script)
    data = client.post("/agent/message", json={"text": "analiza todo"}, headers=headers).json()
    assert data["toolsUsed"] == ["ver_fatiga"] * 4
    assert script.payloads[-1]["forceAnswer"] is True
    assert data["reply"] == "Resumen final."
