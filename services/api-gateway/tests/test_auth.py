from fastapi.testclient import TestClient

REGISTER = {"email": "ana@example.com", "password": "password123", "name": "Ana"}


def _register(client: TestClient, body: dict) -> dict:
    response = client.post("/auth/register", json=body)
    assert response.status_code == 201
    return response.json()


def test_register_login_flow(client: TestClient) -> None:
    data = _register(client, REGISTER)
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["email"] == "ana@example.com"

    response = client.post(
        "/auth/login",
        json={"email": "ana@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_register_duplicate_email(client: TestClient) -> None:
    _register(client, REGISTER)
    response = client.post("/auth/register", json=REGISTER)
    assert response.status_code == 409


def test_login_wrong_password(client: TestClient) -> None:
    _register(client, REGISTER)
    response = client.post(
        "/auth/login",
        json={"email": "ana@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


def test_register_weak_password(client: TestClient) -> None:
    response = client.post(
        "/auth/register",
        json={"email": "weak@example.com", "password": "123", "name": "Weak"},
    )
    assert response.status_code == 422
