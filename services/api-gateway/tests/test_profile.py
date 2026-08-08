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
    }
    response = client.put("/profile", headers=headers, json=body)
    assert response.status_code == 200
    updated = response.json()
    assert updated["weightKg"] == 75.5
    assert updated["heightCm"] == 180
    assert updated["birthYear"] == 1990
    assert updated["goal"] == "performance"
    assert updated["sports"] == ["gym", "boxing"]

    response = client.get("/profile", headers=headers)
    assert response.json()["sports"] == ["gym", "boxing"]


def test_profile_partial_update_keeps_fields(client: TestClient) -> None:
    data = _register(client, REGISTER)
    headers = _auth_headers(data)

    client.put(
        "/profile",
        headers=headers,
        json={"weightKg": 80, "sports": ["running"]},
    )
    response = client.put(
        "/profile", headers=headers, json={"goal": "loss"}
    )
    assert response.status_code == 200
    updated = response.json()
    assert updated["weightKg"] == 80
    assert updated["sports"] == ["running"]
    assert updated["goal"] == "loss"


def test_profile_requires_auth(client: TestClient) -> None:
    response = client.get("/profile")
    assert response.status_code == 401

    response = client.put("/profile", json={"weightKg": 70})
    assert response.status_code == 401
