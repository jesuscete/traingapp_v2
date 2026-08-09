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


def test_create_session_with_flexible_details(client: TestClient) -> None:
    headers = _auth_headers(client)
    payload = {
        "discipline": "gym",
        "rawText": "sesión con detalles",
        "performedAt": "2026-08-08T18:30:00Z",
        "durationMinutes": 45,
        "details": {"plan": "A", "nivel": "intermedio"},
        "exercises": [
            {
                "name": "press banca",
                "sets": 3,
                "reps": 10,
                "weightKg": 60,
                "details": {"rpe": 8, "descanso": 90},
            }
        ],
    }
    response = client.post("/sessions", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["details"]["plan"] == "A"
    assert data["details"]["nivel"] == "intermedio"
    assert data["details"]["kcal_confidence_level"] in ("alta", "media", "baja")
    assert data["exercises"][0]["details"] == {"rpe": 8, "descanso": 90}


def test_estimated_kcal_boxing_with_user_weight(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"email": "luc@example.com", "password": "password123", "name": "Luc"},
    )
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    client.put("/profile", headers=headers, json={"weightKg": 70, "sex": "male"})

    session = client.post(
        "/sessions",
        json={
            "discipline": "boxing",
            "rawText": "clase de boxeo de 1h",
            "performedAt": "2026-08-09T19:00:00Z",
            "durationMinutes": 60,
            "exercises": [],
        },
        headers=headers,
    )
    assert session.status_code == 201
    data = session.json()
    # 7.8 MET × 70 kg × 1h ≈ 546 kcal
    assert data["estimatedKcal"] is not None
    assert abs(data["estimatedKcal"] - 7.8 * 70) < 1


def test_estimated_kcal_null_without_weight(client: TestClient) -> None:
    headers = _auth_headers(client)
    response = client.post("/sessions", json=BOXING_SESSION, headers=headers)
    assert response.status_code == 201
    assert response.json()["estimatedKcal"] is None


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
