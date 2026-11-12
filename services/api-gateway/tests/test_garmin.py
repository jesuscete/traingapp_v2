import base64
import io
import json
import zipfile
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from app.core import crypto, garmin
from app.services.garmin_sync import health_by_day, hrv_score
from tests.fit_builder import running_fit

API_KEY = "personal-key-1234567890"


def _jwt(hours: float = 24) -> str:
    def part(data: dict[str, object]) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    exp = int((datetime.now(UTC) + timedelta(hours=hours)).timestamp())
    return f"{part({'alg': 'HS256'})}.{part({'exp': exp})}.firma"


def _zip(name: str, content: bytes) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(name, content)
    return buffer.getvalue()


class FakeGarmin:
    """Servidor falso de la API personal: registra las llamadas y sirve datos fijos."""

    def __init__(self, start: datetime) -> None:
        self.calls: list[str] = []
        self.token_requests = 0
        self.valid_key = API_KEY
        self.fit = running_fit(start, minutes=30, hr=150, serial=777)
        self.start = start

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.calls.append(path)
        if path == garmin.TOKEN_PATH:
            self.token_requests += 1
            if request.headers.get("Authorization") != f"ApiKey {self.valid_key}":
                return httpx.Response(401)
            return httpx.Response(200, text=_jwt())
        if not request.headers.get("Authorization", "").startswith("Bearer "):
            return httpx.Response(401)
        today = datetime.now(UTC).date().isoformat()
        if path == garmin.SEARCH_PATH:
            start = int(request.url.params["start"])
            items = [
                {
                    "activityId": 111,
                    "activityName": "Carrera",
                    "activityType": {"typeKey": "running"},
                    "startTimeGMT": self.start.strftime("%Y-%m-%d %H:%M:%S"),
                }
            ]
            return httpx.Response(200, json=items if start == 0 else [])
        if path == garmin.DOWNLOAD_PATH.format(activity_id=111):
            return httpx.Response(200, content=_zip("111_ACTIVITY.fit", self.fit))
        if path == garmin.DAILY_SUMMARIES_PATH:
            return httpx.Response(
                200, json={"data": [{"calendarDate": today, "restingHeartRate": 48}]}
            )
        if path == garmin.SLEEP_PATH:
            return httpx.Response(
                200, json=[{"dailySleepDTO": {"calendarDate": today, "sleepTimeSeconds": 27000}}]
            )
        if path.startswith("/hrv-service/hrv/daily/"):
            summaries = [{"calendarDate": today, "lastNightAvg": 66, "weeklyAvg": 60}]
            return httpx.Response(200, json={"hrvSummaries": summaries})
        return httpx.Response(404)


@pytest.fixture()
def fake_garmin(monkeypatch: pytest.MonkeyPatch) -> FakeGarmin:
    fake = FakeGarmin(datetime.now(UTC) - timedelta(hours=5))

    def client() -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url="https://garmin.test", transport=httpx.MockTransport(fake.handler)
        )

    monkeypatch.setattr(garmin, "_client", client)
    return fake


def _headers(client: TestClient, email: str) -> dict[str, str]:
    body = {"email": email, "password": "password123", "name": "G"}
    token = client.post("/auth/register", json=body).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.put("/profile", json={"weightKg": 75, "maxHr": 191}, headers=headers)
    return headers


def test_connect_sync_dedup_and_disconnect(client: TestClient, fake_garmin: FakeGarmin) -> None:
    headers = _headers(client, "garmin@example.com")
    assert client.get("/integrations/garmin", headers=headers).json() == {
        "connected": False,
        "status": None,
        "lastSyncAt": None,
        "lastError": None,
        "lastResult": None,
        "tokenExpiresAt": None,
    }
    bad = client.put("/integrations/garmin", json={"apiKey": "wrong-key-123456"}, headers=headers)
    assert bad.status_code == 400

    ok = client.put("/integrations/garmin", json={"apiKey": API_KEY}, headers=headers)
    assert ok.status_code == 200 and ok.json()["connected"]

    sync = client.post("/integrations/garmin/sync", headers=headers).json()
    assert (sync["imported"], sync["errors"], sync["healthDays"]) == (1, 0, 1), sync
    assert fake_garmin.token_requests == 2  # clave mala + conexión; la sync reutiliza el token

    sessions = client.get("/sessions", headers=headers).json()["items"]
    assert sessions[0]["externalSource"] == "garmin" and sessions[0]["distanceMeters"] == 5400
    profile = client.get("/profile", headers=headers).json()
    assert profile["restingHr"] == 48  # se rellena con la FC en reposo del reloj
    readiness = client.get("/stats/readiness", headers=headers).json()
    assert readiness["sleepHours"] == 7.5 and readiness["restingHr"] == 48
    assert readiness["hrvScore"] == 0.75

    again = client.post("/integrations/garmin/sync", headers=headers).json()
    assert (again["imported"], again["skipped"]) == (0, 1)
    stale = client.post("/integrations/garmin/sync?ifStale=true", headers=headers).json()
    assert stale["imported"] == 0 and stale["status"]["lastSyncAt"]

    assert client.delete("/integrations/garmin", headers=headers).status_code == 204
    assert client.get("/integrations/garmin", headers=headers).json()["connected"] is False
    assert len(client.get("/sessions", headers=headers).json()["items"]) == 1


def test_revoked_key_marks_connection_error(client: TestClient, fake_garmin: FakeGarmin) -> None:
    headers = _headers(client, "garmin-revoked@example.com")
    client.put("/integrations/garmin", json={"apiKey": API_KEY}, headers=headers)
    client.post("/integrations/garmin/sync", headers=headers)
    fake_garmin.valid_key = "otra-clave"  # clave revocada en Garmin Connect
    original = fake_garmin.handler

    def reject_bearer(request: httpx.Request) -> httpx.Response:
        if request.url.path != garmin.TOKEN_PATH:
            return httpx.Response(401)
        return original(request)

    fake_garmin.handler = reject_bearer  # type: ignore[method-assign]
    response = client.post("/integrations/garmin/sync", headers=headers)
    assert response.status_code == 400
    status = client.get("/integrations/garmin", headers=headers).json()
    assert status["status"] == "error" and "Garmin" in status["lastError"]


def test_helpers_are_tolerant() -> None:
    assert hrv_score(60, 60) == 0.5 and hrv_score(80, 60) == 1.0 and hrv_score(None, 60) is None
    days = health_by_day(
        [{"calendarDate": "2026-11-10", "values": {"restingHeartRate": 50}}],
        {"sleep": [{"calendarDate": "2026-11-10", "sleepTimeSeconds": 3600}]},
        None,
    )
    assert days == {date(2026, 11, 10): {"resting_hr": 50.0, "sleep_hours": 1.0}}
    name, content = garmin.unpack_activity_file("9", _zip("dir/9.fit", b"abc"))
    assert (name, content) == ("9.fit", b"abc")
    assert garmin.unpack_activity_file("9", b"raw") == ("9.fit", b"raw")
    assert crypto.decrypt(crypto.encrypt("secreto")) == "secreto"
