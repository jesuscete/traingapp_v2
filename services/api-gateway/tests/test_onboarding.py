from fastapi.testclient import TestClient


def _register(client: TestClient, email: str) -> dict[str, str]:
    body = {"email": email, "password": "password123", "name": " Jota ", "remember": True}
    response = client.post("/auth/register", json=body)
    assert response.status_code == 201, response.text
    assert response.json()["user"]["name"] == "Jota"
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_new_user_onboarding_flow(client: TestClient) -> None:
    headers = _register(client, "nuevo@example.com")
    duplicate = client.post(
        "/auth/register",
        json={"email": "NUEVO@example.com", "password": "password123", "name": "X"},
    )
    assert duplicate.status_code == 409 and "email" in duplicate.json()["detail"]

    state = client.get("/profile/onboarding", headers=headers).json()
    assert state["complete"] is False
    assert {s["key"] for s in state["required"]} == {
        "weight",
        "height",
        "birth_date",
        "sex",
        "primary_sport",
    }
    assert state["pendingRecommended"] == 4

    profile = {
        "weightKg": 78,
        "heightCm": 180,
        "birthDate": "1994-05-20",
        "sex": "male",
        "primarySport": "boxeo",
        "sports": ["boxeo", "triatlon"],
    }
    saved = client.put("/profile", json=profile, headers=headers).json()
    assert saved["birthYear"] == 1994 and saved["birthDate"] == "1994-05-20"

    state = client.get("/profile/onboarding", headers=headers).json()
    assert state["complete"] is True
    pending = {s["key"] for s in state["recommended"] if not s["done"]}
    assert pending == {"garmin", "goal", "max_hr"}  # otros deportes ya hechos

    client.put("/profile", json={"onboardingSkipped": ["garmin", "max_hr"]}, headers=headers)
    client.post("/goals", json={"kind": "competition", "title": "Combate"}, headers=headers)
    state = client.get("/profile/onboarding", headers=headers).json()
    assert state["pendingRecommended"] == 0
