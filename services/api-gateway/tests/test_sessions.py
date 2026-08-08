from fastapi.testclient import TestClient

REGISTER = {"email": "sara@example.com", "password": "password123", "name": "Sara"}

GYM_SESSION = {
    "discipline": "gym",
    "rawText": "5x5 press banca 80kg",
    "performedAt": "2026-08-08T18:30:00Z",
    "durationMinutes": 60,
    "exercises": [{"name": "press banca", "sets": 5, "reps": 5, "weightKg": 80}],
}

BOXING_SESSION = {
    "discipline": "boxing",
    "rawText": "clase de boxeo de 1h30m",
    "performedAt": "2026-08-09T19:00:00Z",
    "durationMinutes": 90,
    "exercises": [],
}


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post("/auth/register", json=REGISTER)
    assert response.status_code == 201
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_and_get_session(client: TestClient) -> None:
    headers = _auth_headers(client)
    response = client.post("/sessions", json=GYM_SESSION, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["volumeKg"] == 2000
    assert data["exercises"][0]["volumeKg"] == 2000
    assert data["rawText"] == "5x5 press banca 80kg"

    fetched = client.get(f"/sessions/{data['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["discipline"] == "gym"


def test_create_boxing_session(client: TestClient) -> None:
    headers = _auth_headers(client)
    response = client.post("/sessions", json=BOXING_SESSION, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["durationMinutes"] == 90
    assert data["volumeKg"] == 0
    assert data["exercises"] == []


def test_list_sessions_ordered_by_date(client: TestClient) -> None:
    headers = _auth_headers(client)
    client.post("/sessions", json=BOXING_SESSION, headers=headers)
    client.post("/sessions", json=GYM_SESSION, headers=headers)
    response = client.get("/sessions", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["rawText"] == "clase de boxeo de 1h30m"


def test_sessions_require_auth(client: TestClient) -> None:
    assert client.post("/sessions", json=GYM_SESSION).status_code == 401
    assert client.get("/sessions").status_code == 401


def test_delete_session(client: TestClient) -> None:
    headers = _auth_headers(client)
    response = client.post("/sessions", json=GYM_SESSION, headers=headers)
    session_id = response.json()["id"]

    deleted = client.delete(f"/sessions/{session_id}", headers=headers)
    assert deleted.status_code == 204

    assert client.get(f"/sessions/{session_id}", headers=headers).status_code == 404
    assert client.delete(f"/sessions/{session_id}", headers=headers).status_code == 404


def test_cannot_access_other_users_session(client: TestClient) -> None:
    headers = _auth_headers(client)
    response = client.post("/sessions", json=GYM_SESSION, headers=headers)
    session_id = response.json()["id"]

    other = client.post(
        "/auth/register",
        json={"email": "otro@example.com", "password": "password123", "name": "Otro"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['access_token']}"}
    assert (
        client.get(f"/sessions/{session_id}", headers=other_headers).status_code == 404
    )
