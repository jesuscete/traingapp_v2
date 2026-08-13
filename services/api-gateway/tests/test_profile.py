from fastapi.testclient import TestClient

from tests.test_auth import REGISTER, _register


def _auth_headers(data: dict) -> dict:
    return {"Authorization": f"Bearer {data['access_token']}"}


def test_profile_empty_and_update(client: TestClient) -> None:
    data = _register(client, REGISTER)
    headers = _auth_headers(data)

    response = client.get("/profile", headers=headers)
    assert response.status_code == 200
    profile = response.json()
    assert profile["weightKg"] is None
    assert profile["sports"] is None

    body = {
        "weightKg": 75.5,
        "heightCm": 180,
        "birthYear": 1990,
        "goal": "performance",
        "sports": ["gym", "boxing"],
        "bodyFatPct": 15.2,
        "fitnessLevel": "intermediate",
        "weeklyAvailability": 4,
        "injuries": [{"bodyPart": "hombro", "note": "luxación 2019"}],
        "goals": ["performance", "boxing"],
    }
    response = client.put("/profile", headers=headers, json=body)
    assert response.status_code == 200
    updated = response.json()
    assert updated["weightKg"] == 75.5
    assert updated["heightCm"] == 180
    assert updated["birthYear"] == 1990
    assert updated["goal"] == "performance"
    assert updated["sports"] == ["gym", "boxing"]
    assert updated["bodyFatPct"] == 15.2
    assert updated["fitnessLevel"] == "intermediate"
    assert updated["weeklyAvailability"] == 4
    assert updated["injuries"] == [{"bodyPart": "hombro", "note": "luxación 2019"}]
    assert updated["goals"] == ["performance", "boxing"]

    response = client.get("/profile", headers=headers)
    assert response.json()["sports"] == ["gym", "boxing"]


def test_profile_partial_update_keeps_fields(client: TestClient) -> None:
    data = _register(client, REGISTER)
    headers = _auth_headers(data)

    client.put(
        "/profile",
        headers=headers,
        json={"weightKg": 80, "sports": ["running"], "fitnessLevel": "advanced"},
    )
    response = client.put(
        "/profile", headers=headers, json={"goal": "loss"}
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["weightKg"] == 80
    assert updated["sports"] == ["running"]
    assert updated["goal"] == "loss"
    assert updated["fitnessLevel"] == "advanced"


def test_profile_requires_auth(client: TestClient) -> None:
    response = client.get("/profile")
    assert response.status_code == 401

    response = client.put("/profile", json={"weightKg": 70})
    assert response.status_code == 401


def test_update_name(client: TestClient) -> None:
    data = _register(client, REGISTER)
    headers = _auth_headers(data)

    response = client.put("/profile", headers=headers, json={"name": "Ana Pérez"})
    assert response.status_code == 200
    assert response.json()["name"] == "Ana Pérez"


def test_change_email_ok(client: TestClient) -> None:
    data = _register(client, REGISTER)
    headers = _auth_headers(data)

    response = client.put("/profile/email", headers=headers, json={"email": "nuevo@example.com"})
    assert response.status_code == 200
    assert response.json()["email"] == "nuevo@example.com"

    response = client.get("/profile", headers=headers)
    assert response.json()["email"] == "nuevo@example.com"

    login = client.post(
        "/auth/login",
        json={"email": "nuevo@example.com", "password": "password123"},
    )
    assert login.status_code == 200


def test_change_email_duplicate(client: TestClient) -> None:
    _register(client, REGISTER)
    other = _register(
        client,
        {"email": "lucas@example.com", "password": "password123", "name": "Lucas"},
    )
    headers = _auth_headers(other)

    response = client.put(
        "/profile/email", headers=headers, json={"email": "ana@example.com"}
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "El email ya está registrado"


def test_change_email_requires_auth(client: TestClient) -> None:
    response = client.put("/profile/email", json={"email": "nuevo@example.com"})
    assert response.status_code == 401


def test_change_password_ok(client: TestClient) -> None:
    data = _register(client, REGISTER)
    headers = _auth_headers(data)

    response = client.put(
        "/profile/password",
        headers=headers,
        json={"currentPassword": "password123", "newPassword": "nueva-password"},
    )
    assert response.status_code == 200

    old_login = client.post(
        "/auth/login",
        json={"email": "ana@example.com", "password": "password123"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/auth/login",
        json={"email": "ana@example.com", "password": "nueva-password"},
    )
    assert new_login.status_code == 200


def test_change_password_wrong_current(client: TestClient) -> None:
    data = _register(client, REGISTER)
    headers = _auth_headers(data)

    response = client.put(
        "/profile/password",
        headers=headers,
        json={"currentPassword": "incorrecta", "newPassword": "nueva-password"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "La contraseña actual no es correcta"


def test_change_password_weak_new(client: TestClient) -> None:
    data = _register(client, REGISTER)
    headers = _auth_headers(data)

    response = client.put(
        "/profile/password",
        headers=headers,
        json={"currentPassword": "password123", "newPassword": "123"},
    )
    assert response.status_code == 422


def test_change_password_requires_auth(client: TestClient) -> None:
    response = client.put(
        "/profile/password",
        json={"currentPassword": "password123", "newPassword": "nueva-password"},
    )
    assert response.status_code == 401
