from fastapi.testclient import TestClient

REVIEW_RESPONSE = {
    "puntosFuertes": ["Buena distribución semanal"],
    "solapamientos": [
        {
            "descripcion": "Hombros se cargan varios días seguidos",
            "grupos": ["Hombros"],
            "dias": ["Lunes", "Miércoles"],
        }
    ],
    "sugerencias": ["Deja 48h entre el trabajo de hombro y boxeo"],
}

_REVIEW_PAYLOAD = [
    {
        "dia": "Lunes",
        "tipo": "gimnasio",
        "nombre": "Press de banca",
        "gruposMusculares": ["Pecho", "Tríceps", "Hombros"],
        "series": 4,
        "repsObjetivo": [8, 8],
        "volumenEstimado": 16,
    }
]


def _auth_headers(client: TestClient, email: str = "rev@example.com") -> dict[str, str]:
    client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "name": "Rev"},
    )
    response = client.post(
        "/auth/login", json={"email": email, "password": "password123"}
    )
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_review_routine_success(client: TestClient, monkeypatch) -> None:
    headers = _auth_headers(client)

    async def _fake_review(name: str, payload: list[dict[str, object]]) -> dict:
        assert name == "Rutina A"
        assert payload, "se esperaba un payload con ejercicios/actividades"
        return REVIEW_RESPONSE

    monkeypatch.setattr("app.api.routine.fetch_routine_review", _fake_review)
    response = client.post(
        "/routines/review",
        json={"routineName": "Rutina A", "days": _REVIEW_PAYLOAD},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["puntosFuertes"] == ["Buena distribución semanal"]
    assert body["solapamientos"][0]["descripcion"].startswith("Hombros")
    assert body["solapamientos"][0]["dias"] == ["Lunes", "Miércoles"]
    assert body["sugerencias"]


def test_review_routine_ia_error_returns_502(client: TestClient, monkeypatch) -> None:
    headers = _auth_headers(client, "rev502@example.com")

    async def _boom(name: str, payload: list[dict[str, object]]) -> dict:
        raise RuntimeError("provider down")

    monkeypatch.setattr("app.api.routine.fetch_routine_review", _boom)
    response = client.post(
        "/routines/review",
        json={"routineName": "Rutina A", "days": _REVIEW_PAYLOAD},
        headers=headers,
    )
    assert response.status_code == 502
    assert "IA" in response.json()["detail"]


def test_review_routine_requires_auth(client: TestClient) -> None:
    response = client.post("/routines/review", json={"routineName": "X", "days": []})
    assert response.status_code == 401