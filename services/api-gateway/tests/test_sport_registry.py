import json
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.schemas.sport_profile import SportProfileDoc
from app.services import sport_registry


def _doc(**overrides: Any) -> dict[str, Any]:
    base = json.loads((sport_registry.PROFILES_DIR / "boxing.json").read_text(encoding="utf-8"))
    return {**base, **overrides}


def test_profiles_load_with_aliases_and_fallback() -> None:
    profiles = sport_registry.load_profiles()
    assert {"boxing", "martial_arts", "generic"} <= set(profiles)
    assert sport_registry.profile_doc("martial_arts").sport == "boxing"
    assert sport_registry.profile_doc("tennis").sport == "generic"
    assert sport_registry.block_weights("boxing", "comba") is not None
    assert sport_registry.block_weights("tennis", "comba") is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"muscle_targets": {"pies": [1, 2]}},
        {"pattern_targets": {"volteretas": 3}},
        {"block_muscle_weights": {"karaoke": {"core": 0.5}}},
        {"block_muscle_weights": {"saco": {"core": 1.5}}},
        {"muscle_targets": {"core": [10, 2]}},
        {"rep_zones_by_phase": {"descarga": {"fuerza": [0.2, 0.5]}}},
        {"campo_inventado": True},
    ],
)
def test_invalid_profiles_are_rejected(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        SportProfileDoc.model_validate(_doc(**overrides))


def test_phase_changes_rep_zones() -> None:
    general = sport_registry.sport_profile("boxing", "general").rep_zones["fuerza"]
    pre = sport_registry.sport_profile("boxing", "precompeticion").rep_zones["fuerza"]
    assert pre[0] > general[0]


def test_compact_summary_is_specific_and_bounded() -> None:
    text = sport_registry.compact_summary("boxing")
    assert text.startswith("PERFIL DE BOXEO")
    for expected in ("Potencia rotacional", "press Pallof", "víspera", "hombro"):
        assert expected in text
    assert len(text) < 3200  # ~800 tokens como máximo


def test_agent_tool_returns_profile(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    body = {"email": "profile-tool@example.com", "password": "password123", "name": "P"}
    token = client.post("/auth/register", json=body).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    steps = [
        {"source": "llm", "action": "herramienta", "tool": "perfil_deporte", "arguments": {}},
        {"source": "llm", "action": "responder", "message": "Ok", "arguments": {}},
    ]
    seen: list[dict[str, Any]] = []

    async def scripted(payload: dict[str, Any]) -> dict[str, Any]:
        seen.append(payload)
        return steps.pop(0)

    monkeypatch.setattr("app.core.agent.fetch_agent_step", scripted)
    client.post("/agent/message", json={"text": "¿qué necesita el boxeo?"}, headers=headers)
    assert "PERFIL DE BOXEO" in seen[1]["messages"][-1]["content"]
