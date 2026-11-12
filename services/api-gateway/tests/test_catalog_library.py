from typing import Any

from fastapi.testclient import TestClient


def _headers(client: TestClient, email: str) -> dict[str, str]:
    client.post("/auth/register", json={"email": email, "password": "password123", "name": "L"})
    response = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _press(client: TestClient, headers: dict[str, str]) -> dict[str, Any]:
    items = client.get("/catalog/exercises", headers=headers).json()
    return next(i for i in items if i["normalizedName"] == "press banca")


def _gym(day: int, sets: list[tuple[int, float]], warmup: bool = False) -> dict[str, Any]:
    return {
        "rawText": "gym",
        "performedAt": f"2026-09-{day:02d}T18:00:00Z",
        "durationMinutes": 60,
        "exercises": [
            {
                "name": "press banca",
                "orderIndex": 0,
                "sets": [
                    {
                        "setNumber": n,
                        "isWarmup": warmup and n == 1,
                        "setType": "calentamiento" if warmup and n == 1 else "normal",
                        "entries": [{"entryOrder": 0, "reps": reps, "weight": weight}],
                    }
                    for n, (reps, weight) in enumerate(sets, start=1)
                ],
            }
        ],
    }


def test_favorites_toggle(client: TestClient, seed_catalog) -> None:
    headers = _headers(client, "fav@example.com")
    press = _press(client, headers)
    assert press["isFavorite"] is False

    url = f"/catalog/exercises/{press['id']}/favorite"
    assert client.put(url, headers=headers).status_code == 204
    assert client.put(url, headers=headers).status_code == 204
    assert _press(client, headers)["isFavorite"] is True

    other = _headers(client, "nofav@example.com")
    assert _press(client, other)["isFavorite"] is False

    assert client.delete(url, headers=headers).status_code == 204
    assert _press(client, headers)["isFavorite"] is False


def test_favorite_unknown_exercise_404(client: TestClient) -> None:
    headers = _headers(client, "fav404@example.com")
    url = "/catalog/exercises/00000000-0000-0000-0000-000000000000/favorite"
    assert client.put(url, headers=headers).status_code == 404


def test_history_records_and_isolation(client: TestClient, seed_catalog) -> None:
    headers = _headers(client, "hist@example.com")
    press = _press(client, headers)
    for body in (_gym(1, [(10, 40), (5, 80), (5, 80)], warmup=True), _gym(8, [(3, 90)])):
        assert client.post("/sessions/gym", json=body, headers=headers).status_code == 201

    data = client.get(f"/catalog/exercises/{press['id']}/history", headers=headers).json()
    assert [s["performedAt"][:10] for s in data["sessions"]] == ["2026-09-08", "2026-09-01"]
    assert data["records"]["maxWeightKg"] == 90
    assert data["records"]["bestSessionVolumeKg"] == 800
    assert [p["topWeightKg"] for p in data["progress"]] == [80, 90]
    assert data["sessions"][1]["sets"][0]["e1rmKg"] is None
    assert data["records"]["bestE1rmKg"] == 97.6

    last = client.get(f"/catalog/exercises/{press['id']}/history?limit=1", headers=headers)
    assert len(last.json()["sessions"]) == 1

    stranger = _headers(client, "stranger@example.com")
    empty = client.get(f"/catalog/exercises/{press['id']}/history", headers=stranger).json()
    assert empty["sessions"] == [] and empty["records"]["maxWeightKg"] is None
