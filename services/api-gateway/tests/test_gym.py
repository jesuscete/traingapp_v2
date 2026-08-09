from fastapi.testclient import TestClient

REGISTER = {"email": "gym@example.com", "password": "password123", "name": "Gym"}


def _auth_headers(client: TestClient, email: str = REGISTER["email"]) -> dict[str, str]:
    client.post("/auth/register", json={"email": email, "password": "password123", "name": "Gym"})
    response = client.post("/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _entry(
    order: int,
    *,
    reps: int | None = None,
    weight: float | None = None,
    weight_unit: str = "kg",
    rpe: int | None = None,
    side: str = "both",
    duration: float | None = None,
) -> dict:
    data = {"entryOrder": order, "weightUnit": weight_unit, "side": side}
    if reps is not None:
        data["reps"] = reps
    if weight is not None:
        data["weight"] = weight
    if rpe is not None:
        data["rpe"] = rpe
    if duration is not None:
        data["durationSeconds"] = duration
    return data


def _set(
    number: int,
    entries: list[dict],
    *,
    set_type: str = "normal",
    is_warmup: bool = False,
    rest_seconds: int | None = None,
) -> dict:
    data = {"setNumber": number, "setType": set_type, "isWarmup": is_warmup, "entries": entries}
    if rest_seconds is not None:
        data["restSeconds"] = rest_seconds
    return data


def _session(*exercises: dict) -> dict:
    return {
        "rawText": "entreno gym",
        "performedAt": "2026-08-09T18:30:00Z",
        "durationMinutes": 60,
        "exercises": list(exercises),
    }


def _exercise(
    name: str, sets: list[dict], *, order: int = 0, superset_group: str | None = None
) -> dict:
    data = {"name": name, "orderIndex": order, "sets": sets}
    if superset_group is not None:
        data["supersetGroupId"] = superset_group
    return data


def test_create_gym_session_normal_sets(client: TestClient) -> None:
    headers = _auth_headers(client)
    sets = [
        _set(1, [_entry(0, reps=5, weight=80, rpe=8)]),
        _set(2, [_entry(0, reps=5, weight=80, rpe=9)]),
        _set(3, [_entry(0, reps=5, weight=80, rpe=10)]),
    ]
    response = client.post(
        "/sessions/gym", json=_session(_exercise("press banca", sets)), headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["volumeKg"] == 3 * 5 * 80
    assert data["summary"]["totalVolume"] == 3 * 5 * 80
    assert data["summary"]["setsCount"] == 3
    assert data["summary"]["avgRpe"] == 9.0
    assert data["summary"]["durationMin"] == 60
    assert len(data["workoutExercises"]) == 1
    assert len(data["workoutExercises"][0]["sets"]) == 3
    assert data["workoutExercises"][0]["sets"][0]["entries"][0]["weight"] == 80


def test_warmup_sets_excluded_from_volume(client: TestClient) -> None:
    headers = _auth_headers(client)
    sets = [
        _set(1, [_entry(0, reps=5, weight=20)], is_warmup=True),
        _set(2, [_entry(0, reps=5, weight=40)], is_warmup=True),
        _set(3, [_entry(0, reps=5, weight=60)]),
        _set(4, [_entry(0, reps=5, weight=70)]),
        _set(5, [_entry(0, reps=5, weight=80)]),
    ]
    response = client.post(
        "/sessions/gym", json=_session(_exercise("sentadilla", sets)), headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["volumeKg"] == (60 + 70 + 80) * 5
    assert data["summary"]["setsCount"] == 3
    assert data["workoutExercises"][0]["sets"][0]["isWarmup"] is True
    assert data["workoutExercises"][0]["sets"][0]["volumeKg"] == 0.0


def test_dropset_accumulates_entries(client: TestClient) -> None:
    headers = _auth_headers(client)
    sets = [
        _set(1, [_entry(0, reps=8, weight=60)]),
        _set(
            2,
            [
                _entry(0, reps=5, weight=80, rpe=10),
                _entry(1, reps=5, weight=60),
                _entry(2, reps=8, weight=40),
            ],
            set_type="dropset",
            rest_seconds=90,
        ),
    ]
    response = client.post(
        "/sessions/gym", json=_session(_exercise("press banca", sets)), headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    working = data["workoutExercises"][0]["sets"]
    assert working[1]["setType"] == "dropset"
    assert len(working[1]["entries"]) == 3
    assert [e["weight"] for e in working[1]["entries"]] == [80, 60, 40]
    # dropset: sin descanso entre tramos
    assert working[1]["restSeconds"] is None
    assert data["volumeKg"] == 60 * 8 + 80 * 5 + 60 * 5 + 40 * 8


def test_bodyweight_volume_adds_user_weight(client: TestClient, seed_catalog) -> None:
    headers = _auth_headers(client, "bw@example.com")
    client.put("/profile", json={"weightKg": 78}, headers=headers)
    sets = [
        _set(1, [_entry(0, reps=8, weight=0)]),
        _set(2, [_entry(0, reps=8, weight=0)]),
        _set(3, [_entry(0, reps=8, weight=10, rpe=9)]),
    ]
    response = client.post(
        "/sessions/gym", json=_session(_exercise("dominadas", sets)), headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    # (78+0)*8*2 + (78+10)*8
    assert data["volumeKg"] == 78 * 8 * 2 + 88 * 8


def test_volume_uses_only_added_weight_without_profile(client: TestClient, seed_catalog) -> None:
    headers = _auth_headers(client, "bw2@example.com")
    sets = [_set(1, [_entry(0, reps=8, weight=10)])]
    response = client.post(
        "/sessions/gym", json=_session(_exercise("dominadas", sets)), headers=headers
    )
    assert response.status_code == 201
    # sin peso corporal registrado: solo lastre anadido
    assert response.json()["volumeKg"] == 10 * 8


def test_lb_weight_normalized_to_kg(client: TestClient) -> None:
    headers = _auth_headers(client, "lb@example.com")
    sets = [_set(1, [_entry(0, reps=10, weight=100, weight_unit="lb")])]
    response = client.post(
        "/sessions/gym", json=_session(_exercise("press banca", sets)), headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    entry = data["workoutExercises"][0]["sets"][0]["entries"][0]
    assert entry["weightUnit"] == "lb"
    assert abs(entry["weight"] - 100 * 0.45359237) < 0.001
    assert abs(data["volumeKg"] - 100 * 0.45359237 * 10) < 0.01


def test_unilateral_sides_preserved(client: TestClient) -> None:
    headers = _auth_headers(client, "uni@example.com")
    sets = [
        _set(1, [_entry(0, reps=10, weight=20, side="left")]),
        _set(2, [_entry(0, reps=10, weight=20, side="right")]),
    ]
    response = client.post(
        "/sessions/gym", json=_session(_exercise("zancadas", sets)), headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    entries = [e for ws in data["workoutExercises"][0]["sets"] for e in ws["entries"]]
    assert [e["side"] for e in entries] == ["left", "right"]
    assert data["volumeKg"] == 2 * 10 * 20


def test_same_exercise_twice_allowed(client: TestClient) -> None:
    headers = _auth_headers(client, "dup@example.com")
    first = _exercise("sentadilla", [_set(1, [_entry(0, reps=5, weight=60)])], order=0)
    second = _exercise("sentadilla", [_set(1, [_entry(0, reps=3, weight=80)])], order=1)
    response = client.post("/sessions/gym", json=_session(first, second), headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert len(data["workoutExercises"]) == 2
    assert [we["orderIndex"] for we in data["workoutExercises"]] == [0, 1]
    assert data["volumeKg"] == 60 * 5 + 80 * 3


def test_isometric_set_zero_volume(client: TestClient) -> None:
    headers = _auth_headers(client, "iso@example.com")
    sets = [
        _set(1, [_entry(0, duration=45)], set_type="isometrico"),
        _set(2, [_entry(0, duration=40)], set_type="isometrico"),
    ]
    response = client.post(
        "/sessions/gym", json=_session(_exercise("plancha", sets)), headers=headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["volumeKg"] == 0
    assert data["workoutExercises"][0]["sets"][0]["entries"][0]["durationSeconds"] == 45
    assert data["summary"]["setsCount"] == 2


def test_get_gym_session_detail(client: TestClient) -> None:
    headers = _auth_headers(client)
    response = client.post(
        "/sessions/gym",
        json=_session(_exercise("press banca", [_set(1, [_entry(0, reps=5, weight=80)])])),
        headers=headers,
    )
    session_id = response.json()["id"]

    detail = client.get(f"/sessions/gym/{session_id}", headers=headers)
    assert detail.status_code == 200
    data = detail.json()
    assert data["id"] == session_id
    assert data["summary"]["totalVolume"] == 400
    assert data["workoutExercises"][0]["name"] == "press banca"

    detail_legacy = client.get(f"/sessions/{session_id}", headers=headers)
    assert detail_legacy.status_code == 200
    assert detail_legacy.json()["volumeKg"] == 400


def test_superset_group_roundtrip(client: TestClient) -> None:
    headers = _auth_headers(client, "sup@example.com")
    group = "550e8400-e29b-41d4-a716-446655440000"
    a = _exercise(
        "press inclinado", [_set(1, [_entry(0, reps=8, weight=40)])], superset_group=group
    )
    b = _exercise("aperturas", [_set(1, [_entry(0, reps=12, weight=15)])], superset_group=group)
    response = client.post("/sessions/gym", json=_session(a, b), headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert [we["supersetGroupId"] for we in data["workoutExercises"]] == [group, group]


def test_gym_sessions_require_auth(client: TestClient) -> None:
    assert client.post("/sessions/gym", json=_session()).status_code == 401
    assert client.get("/sessions/gym").status_code == 401


def test_normal_set_rejects_multiple_entries(client: TestClient) -> None:
    headers = _auth_headers(client, "bad-normal@example.com")
    sets = [_set(1, [_entry(0, reps=5, weight=80), _entry(1, reps=5, weight=60)])]
    response = client.post(
        "/sessions/gym", json=_session(_exercise("press banca", sets)), headers=headers
    )
    assert response.status_code == 422


def test_dropset_requires_two_entries(client: TestClient) -> None:
    headers = _auth_headers(client, "bad-drop@example.com")
    sets = [_set(1, [_entry(0, reps=5, weight=80)], set_type="dropset")]
    response = client.post(
        "/sessions/gym", json=_session(_exercise("press banca", sets)), headers=headers
    )
    assert response.status_code == 422


def test_list_gym_sessions(client: TestClient) -> None:
    headers = _auth_headers(client, "list@example.com")
    client.post(
        "/sessions/gym",
        json=_session(_exercise("press banca", [_set(1, [_entry(0, reps=5, weight=80)])])),
        headers=headers,
    )
    client.post(
        "/sessions/gym",
        json=_session(_exercise("sentadilla", [_set(1, [_entry(0, reps=5, weight=60)])])),
        headers=headers,
    )
    response = client.get("/sessions/gym", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["summary"]["totalVolume"] > 0
