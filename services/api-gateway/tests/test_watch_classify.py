"""Entrenos del reloj sin catalogar (ADR-012)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.schemas.watch import ClassifyPreviewOut
from app.services import watch_classify
from tests.fit_builder import cardio_fit, running_fit
from tests.test_activity_import import _headers, _import

START = datetime.now(UTC).replace(microsecond=0) - timedelta(days=1)


def _import_cardio(client: TestClient, headers: dict[str, str]) -> str:
    response = _import(client, headers, "cardio.fit", cardio_fit(START))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "imported" and body["discipline"] == "other"
    return str(body["sessionId"])


def test_cardio_import_is_pending_and_running_is_not(client: TestClient) -> None:
    headers = _headers(client, "watch-pending@example.com")
    session_id = _import_cardio(client, headers)
    _import(client, headers, "run.fit", running_fit(START - timedelta(hours=5)))

    items = client.get("/sessions/unclassified", headers=headers).json()["items"]
    assert [i["id"] for i in items] == [session_id]
    assert items[0]["subSport"] == "cardio_training"
    assert items[0]["estimatedKcal"] == 610
    assert items[0]["avgHeartRate"] is not None


def test_classify_as_hyrox_keeps_watch_data(client: TestClient) -> None:
    headers = _headers(client, "watch-classify@example.com")
    session_id = _import_cardio(client, headers)
    before = client.get(f"/sessions/{session_id}", headers=headers).json()

    response = client.post(
        f"/sessions/{session_id}/classify",
        json={
            "discipline": "hyrox",
            "note": "4 estaciones: SkiErg, trineo, burpees y wall balls",
            "intensity": 8,
            "exercises": [{"name": "Wall balls", "sets": 4, "reps": 25}],
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["discipline"] == "hyrox"
    assert data["rawText"].startswith("HYROX")
    assert data["estimatedKcal"] == 610  # las kcal del reloj no se recalculan
    assert data["details"]["activity"]["avgHr"] == before["details"]["activity"]["avgHr"]
    assert data["details"]["classification"]["status"] == "done"
    assert [e["name"] for e in data["exercises"]] == ["Wall balls"]
    assert client.get("/sessions/unclassified", headers=headers).json()["items"] == []

    # Editar después tampoco pisa las kcal del reloj.
    edited = client.put(f"/sessions/{session_id}", json={"intensity": 6}, headers=headers)
    assert edited.json()["estimatedKcal"] == 610


def test_skip_is_not_asked_again(client: TestClient) -> None:
    headers = _headers(client, "watch-skip@example.com")
    session_id = _import_cardio(client, headers)
    assert client.post(f"/sessions/{session_id}/classify/skip", headers=headers).status_code == 204
    assert client.get("/sessions/unclassified", headers=headers).json()["items"] == []
    detail = client.get(f"/sessions/{session_id}", headers=headers).json()
    assert detail["discipline"] == "other"
    assert detail["details"]["classification"]["status"] == "skipped"


def test_manual_sessions_cannot_be_classified(client: TestClient) -> None:
    headers = _headers(client, "watch-manual@example.com")
    created = client.post(
        "/sessions",
        json={
            "discipline": "other",
            "rawText": "algo",
            "performedAt": START.isoformat(),
            "durationMinutes": 30,
        },
        headers=headers,
    ).json()
    response = client.post(
        f"/sessions/{created['id']}/classify", json={"discipline": "boxing"}, headers=headers
    )
    assert response.status_code == 422
    other_user = _headers(client, "watch-other@example.com")
    assert (
        client.post(f"/sessions/{created['id']}/classify/skip", headers=other_user).status_code
        == 404
    )


def test_preview_uses_ai_draft(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    headers = _headers(client, "watch-preview@example.com")

    async def fake_preview(text: str) -> ClassifyPreviewOut:
        assert "hyrox" in text
        return ClassifyPreviewOut(discipline="hyrox", exercises=[], intensity=8)

    monkeypatch.setattr(watch_classify, "preview", fake_preview)
    response = client.post(
        "/sessions/classify/preview", json={"text": "hice un hyrox simulado"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["discipline"] == "hyrox"
