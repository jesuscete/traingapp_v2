from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient

from app.analytics import fatigue as fatigue_analytics
from app.schemas.metrics import CombatBlock, CombatMetrics
from app.services.fatigue_input import combat_strikes


def _headers(client: TestClient, email: str) -> dict[str, str]:
    body = {"email": email, "password": "password123", "name": "M"}
    return {
        "Authorization": f"Bearer {client.post('/auth/register', json=body).json()['access_token']}"
    }


def _iso(days_ago: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days_ago)).isoformat().replace("+00:00", "Z")


def _session(discipline: str, days_ago: int = 0, **extra: Any) -> dict[str, Any]:
    return {
        "discipline": discipline,
        "rawText": f"{discipline} test",
        "performedAt": _iso(days_ago),
        **extra,
    }


BOXING_METRICS = {
    "kind": "combat",
    "blocks": [
        {"type": "saco", "rounds": 5, "roundSeconds": 180},
        {"type": "comba", "minutes": 10},
        {"type": "sparring", "rounds": 3, "roundSeconds": 120},
    ],
}


def test_combat_metrics_stored_and_duration_derived(client: TestClient) -> None:
    headers = _headers(client, "combat@example.com")
    response = client.post(
        "/sessions", json=_session("boxing", metrics=BOXING_METRICS, intensity=8), headers=headers
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["durationMinutes"] == 31  # 15 saco + 10 comba + 6 sparring
    assert data["details"]["metrics"]["blocks"][0] == {
        "type": "saco",
        "rounds": 5,
        "roundSeconds": 180,
    }


def test_endurance_metrics_fill_columns(client: TestClient) -> None:
    headers = _headers(client, "endurance@example.com")
    metrics = {
        "kind": "endurance",
        "distanceMeters": 10000,
        "avgHeartRate": 152,
        "elevationGainM": 120,
    }
    response = client.post(
        "/sessions",
        json=_session("running", durationMinutes=55, metrics=metrics),
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["distanceMeters"] == 10000


def test_metrics_must_match_discipline(client: TestClient) -> None:
    headers = _headers(client, "mismatch@example.com")
    endurance = {"kind": "endurance", "distanceMeters": 5000}
    bad_kind = client.post("/sessions", json=_session("boxing", metrics=endurance), headers=headers)
    assert bad_kind.status_code == 422
    gym = client.post("/sessions", json=_session("gym", metrics=BOXING_METRICS), headers=headers)
    assert gym.status_code == 422
    empty_block = {"kind": "combat", "blocks": [{"type": "saco"}]}
    no_duration = client.post(
        "/sessions", json=_session("boxing", metrics=empty_block), headers=headers
    )
    assert no_duration.status_code == 422
    generic_ok = {"kind": "generic", "notes": "clase suave"}
    assert (
        client.post(
            "/sessions", json=_session("boxing", metrics=generic_ok), headers=headers
        ).status_code
        == 201
    )


def test_combat_strikes_by_block_type() -> None:
    metrics = CombatMetrics(
        blocks=[
            CombatBlock(type="saco", rounds=3, round_seconds=180),
            CombatBlock(type="sombra", minutes=5),
            CombatBlock(type="sparring", rounds=2, strikes=150),
        ]
    )
    assert combat_strikes(metrics) == 3 * 3 * 100 + 5 * 60 + 150


def test_fatigue_uses_intensity_column(client: TestClient) -> None:
    low = _headers(client, "rpe-low@example.com")
    high = _headers(client, "rpe-high@example.com")
    for headers, intensity in ((low, 3), (high, 9)):
        body = _session("boxing", durationMinutes=60, metrics=BOXING_METRICS, intensity=intensity)
        assert client.post("/sessions", json=body, headers=headers).status_code == 201

    def shoulders(headers: dict[str, str]) -> float:
        muscles = client.get("/stats/fatigue", headers=headers).json()["muscles"]
        return next(m["fatigue"] for m in muscles if m["muscleGroup"] == "shoulders")

    assert shoulders(low) > 0
    assert abs(shoulders(high) - 3 * shoulders(low)) <= 0.3


def test_fatigue_explain_adds_up_to_current_fatigue(client: TestClient) -> None:
    headers = _headers(client, "explain@example.com")
    for days_ago in (3, 1):
        body = _session("boxing", days_ago=days_ago, metrics=BOXING_METRICS, intensity=8)
        assert client.post("/sessions", json=body, headers=headers).status_code == 201
    run = _session("running", days_ago=0, durationMinutes=40, intensity=6)
    assert client.post("/sessions", json=run, headers=headers).status_code == 201

    fatigue = client.get("/stats/fatigue", headers=headers).json()["muscles"]
    shoulders = next(m["fatigue"] for m in fatigue if m["muscleGroup"] == "shoulders")

    explain = client.get("/stats/fatigue/explain?group=shoulders", headers=headers)
    assert explain.status_code == 200, explain.text
    data = explain.json()
    assert abs(data["fatigue"] - shoulders) <= 0.5
    assert data["sessions"][0]["discipline"] == "boxing"
    remaining = [s["remaining"] for s in data["sessions"]]
    assert remaining == sorted(remaining, reverse=True)
    assert abs(sum(s["share"] for s in data["sessions"]) - 1) < 0.05

    assert client.get("/stats/fatigue/explain?group=pies", headers=headers).status_code == 422


def test_cycling_distance_drives_volume() -> None:
    short = fatigue_analytics.SessionData(discipline="cycling", distance_meters=10_000)
    long = fatigue_analytics.SessionData(discipline="cycling", distance_meters=40_000)
    assert fatigue_analytics.relative_volume(short) == 0.25
    assert fatigue_analytics.relative_volume(long) == 1.0


def test_update_session_metrics_and_header(client: TestClient) -> None:
    headers = _headers(client, "edit@example.com")
    client.put("/profile", json={"weightKg": 75}, headers=headers)
    created = client.post(
        "/sessions", json=_session("boxing", durationMinutes=60, intensity=5), headers=headers
    ).json()
    url = f"/sessions/{created['id']}"
    kcal_before = created["estimatedKcal"]

    updated = client.put(
        url, json={"intensity": 9, "note": "Muy dura", "metrics": BOXING_METRICS}, headers=headers
    )
    assert updated.status_code == 200, updated.text
    data = updated.json()
    assert data["intensity"] == 9
    assert data["note"] == "Muy dura"
    assert data["durationMinutes"] == 60  # no se pisa una duración ya registrada
    assert len(data["details"]["metrics"]["blocks"]) == 3
    assert data["estimatedKcal"] > kcal_before

    wrong = client.put(url, json={"metrics": {"kind": "climbing", "routes": []}}, headers=headers)
    assert wrong.status_code == 422

    stranger = _headers(client, "edit-stranger@example.com")
    assert client.put(url, json={"note": "x"}, headers=stranger).status_code == 404


def test_update_gym_session_header_only(client: TestClient) -> None:
    headers = _headers(client, "edit-gym@example.com")
    gym = {
        "rawText": "gym",
        "performedAt": _iso(0),
        "durationMinutes": 50,
        "exercises": [
            {
                "name": "press banca",
                "orderIndex": 0,
                "sets": [{"setNumber": 1, "entries": [{"entryOrder": 0, "reps": 5, "weight": 80}]}],
            }
        ],
    }
    created = client.post("/sessions/gym", json=gym, headers=headers).json()
    url = f"/sessions/{created['id']}"
    ok = client.put(url, json={"durationMinutes": 65, "note": "Buen día"}, headers=headers)
    assert ok.status_code == 200, ok.text
    assert (ok.json()["durationMinutes"], ok.json()["note"]) == (65, "Buen día")
    assert client.put(url, json={"metrics": BOXING_METRICS}, headers=headers).status_code == 422
