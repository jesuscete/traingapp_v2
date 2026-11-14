import json
from typing import Any

import httpx
from fastapi.testclient import TestClient

from app.analytics.patterns import exercise_patterns, similarity
from app.analytics.sport_analysis import ExerciseWork, analyze
from app.services.sport_registry import sport_profile

BOXING = sport_profile("boxing")


def _work(
    name: str, muscles: dict[str, float], reps: list[int], day: int | None = None, **kw: Any
) -> ExerciseWork:
    return ExerciseWork(None, name, muscles, exercise_patterns(name, muscles, **kw), reps, day)


def test_patterns_word_start_and_plurals() -> None:
    assert exercise_patterns(
        "Medicine Ball Throw", {"chest": 0.6}, category="plyometrics", force="push"
    ) >= {"pliometria"}
    assert "tiron_horizontal" not in exercise_patterns("Medicine Ball Throw", {"chest": 0.6})
    assert exercise_patterns("Dumbbell Lunges", {"quadriceps": 1}) == {"unilateral"}
    assert exercise_patterns("x", {"core": 1}, name_es="Giro ruso con disco") == frozenset()
    assert "rotacion" in exercise_patterns("Russian Twist", {"core": 1})


def test_boxing_analysis_finds_gaps_and_imbalance() -> None:
    work = [
        _work("Press banca", {"chest": 1, "triceps": 0.5}, [8, 8, 8, 8], day=2, force="push"),
        _work("Press militar", {"shoulders": 1}, [8, 8, 8], day=2, force="push"),
        _work("Remo con barra", {"back": 1}, [10, 10], day=4, force="pull"),
        _work("Sentadilla", {"quadriceps": 1, "glutes": 0.6}, [5, 5, 5, 5, 5, 5], day=4),
    ]
    result = analyze(work, BOXING, weeks=1, sport_days={3, 5})
    codes = {g.code for g in result.gaps}
    assert "pattern:rotacion" in codes and "pattern:cuello" in codes
    assert "balance:pull_push" in codes  # 7 empuje vs 2 tirón
    assert result.pull_push_ratio == round(2 / 7, 2)
    assert result.patterns["rotacion"].status == "missing"
    # Jueves pierna pesada (6 series) y viernes deporte.
    assert any(g.code == "conflict:4->5" for g in result.gaps)
    assert result.gaps[0].severity == "alta"
    assert 0 <= result.score < 60


def test_similarity_prefers_same_muscles_and_force() -> None:
    bench = ({"chest": 1.0, "triceps": 0.5}, frozenset({"empuje_horizontal"}), "push")
    dumbbell = ({"chest": 1.0, "triceps": 0.4}, frozenset({"empuje_horizontal"}), "push")
    squat = ({"quadriceps": 1.0}, frozenset({"sentadilla"}), "push")
    assert similarity(*bench, *dumbbell) > 0.9
    assert similarity(*bench, *squat) < 0.3


def _headers(client: TestClient, email: str) -> dict[str, str]:
    body = {"email": email, "password": "password123", "name": "A"}
    token = client.post("/auth/register", json=body).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _ids(client: TestClient, headers: dict[str, str]) -> dict[str, str]:
    return {
        e["normalizedName"]: e["id"]
        for e in client.get("/catalog/exercises", headers=headers).json()
    }


def _day(dow: int, exercise_ids: list[str]) -> dict[str, Any]:
    return {
        "dayOfWeek": dow,
        "dayType": "gimnasio",
        "exercises": [
            {
                "exerciseId": eid,
                "orderIndex": i,
                "sets": [
                    {"setNumber": n, "targetRepsMin": 8, "targetRepsMax": 10} for n in (1, 2, 3)
                ],
            }
            for i, eid in enumerate(exercise_ids)
        ],
    }


def test_sport_analysis_endpoint_uses_routine_and_suggests(
    client: TestClient, seed_catalog
) -> None:
    headers = _headers(client, "boxer@example.com")
    ids = _ids(client, headers)
    routine = {
        "name": "Boxeo",
        "days": [
            _day(1, [ids["press banca"], ids["press militar"], ids["fondos en paralelas"]]),
        ],
    }
    assert client.post("/routines", json=routine, headers=headers).status_code == 201

    response = client.get("/analysis/sport?sport=boxing", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["basis"] == "rutina" and data["sport"] == "boxing"
    gaps = {g["code"]: g for g in data["gaps"]}
    assert "pattern:rotacion" in gaps
    assert any(s["name"] for s in gaps["pattern:rotacion"]["suggestions"])
    assert "balance:pull_push" in gaps

    empty = client.get("/analysis/sport", headers=_headers(client, "nobody@example.com")).json()
    assert empty["basis"] == "sin_datos"


def test_alternatives_and_one_click_swap(client: TestClient, seed_catalog) -> None:
    headers = _headers(client, "swap@example.com")
    ids = _ids(client, headers)
    alts = client.get(
        f"/catalog/exercises/{ids['press banca']}/alternatives?limit=5", headers=headers
    )
    assert alts.status_code == 200, alts.text
    names = [a["name"].lower() for a in alts.json()]
    assert ids["press banca"] not in [a["exerciseId"] for a in alts.json()]
    assert any("press" in n or "aperturas" in n or "fondos" in n for n in names[:3])

    created = client.post(
        "/routines", json={"name": "R", "days": [_day(1, [ids["press banca"]])]}, headers=headers
    ).json()
    entry_id = created["days"][0]["exercises"][0]["id"]
    swapped = client.post(
        f"/routines/{created['id']}/exercises/{entry_id}/swap",
        json={"exerciseId": ids["press con mancuernas"]},
        headers=headers,
    )
    assert swapped.status_code == 200, swapped.text
    exercise = swapped.json()["days"][0]["exercises"][0]
    assert exercise["exerciseId"] == ids["press con mancuernas"] and len(exercise["sets"]) == 3

    added = client.post(
        f"/routines/{created['id']}/days/1/exercises",
        json={
            "exerciseId": ids["russian twist"],
            "sets": 3,
            "targetRepsMin": 12,
            "targetRepsMax": 15,
        },
        headers=headers,
    )
    assert added.status_code == 200, added.text
    assert added.json()["days"][0]["exercises"][-1]["exerciseId"] == ids["russian twist"]
    no_day = client.post(
        f"/routines/{created['id']}/days/3/exercises",
        json={"exerciseId": ids["russian twist"]},
        headers=headers,
    )
    assert no_day.status_code == 422

    stranger = _headers(client, "swap-stranger@example.com")
    url = f"/routines/{created['id']}/exercises/{entry_id}/swap"
    assert (
        client.post(url, json={"exerciseId": ids["sentadilla"]}, headers=stranger).status_code
        == 404
    )


def test_sport_analysis_narrative(
    client: TestClient, seed_catalog, monkeypatch, _fake_redis
) -> None:
    headers = _headers(client, "narrative@example.com")
    ids = _ids(client, headers)
    routine = {"name": "R", "days": [_day(1, [ids["press banca"]])]}
    assert client.post("/routines", json=routine, headers=headers).status_code == 201

    calls: list[dict[str, object]] = []

    async def fake(label: str, analysis: dict[str, object]) -> dict[str, object]:
        calls.append(analysis)
        sent = json.dumps(analysis)  # el cliente real lo envía como JSON
        assert "gaps" in analysis and "score" in analysis
        assert str(analysis["perfilDeporte"]).startswith("PERFIL DE BOXEO")
        assert "exerciseId" not in sent and "imageUrl" not in sent  # payload compacto (M10)
        return {
            "source": "llm",
            "resumen": f"Diagnóstico para {label}.",
            "prioridades": ["Rotación"],
        }

    monkeypatch.setattr("app.api.analysis.fetch_sport_narrative", fake)
    data = client.get("/analysis/sport?sport=boxing&narrative=true", headers=headers).json()
    assert data["narrative"] == {
        "source": "llm",
        "resumen": "Diagnóstico para Boxeo.",
        "prioridades": ["Rotación"],
    }

    again = client.get("/analysis/sport?sport=boxing&narrative=true", headers=headers).json()
    assert again["narrative"] == data["narrative"] and len(calls) == 1  # de la caché

    async def down(label: str, analysis: dict[str, object]) -> dict[str, object]:
        raise httpx.ConnectError("ai-parser caído")

    _fake_redis.lists.clear()

    monkeypatch.setattr("app.api.analysis.fetch_sport_narrative", down)
    data = client.get("/analysis/sport?sport=boxing&narrative=true", headers=headers).json()
    assert data["narrative"]["source"] == "fallback"
    assert data["narrative"]["prioridades"]


def _gym_session(client: TestClient, headers: dict[str, str], names: list[str]) -> None:
    from datetime import UTC, datetime

    from test_gym import _entry, _exercise, _session, _set

    exercises = [
        _exercise(name, [_set(n, [_entry(0, reps=6, weight=40)]) for n in (1, 2, 3)], order=i)
        for i, name in enumerate(names)
    ]
    payload = _session(exercises[0])
    payload["exercises"] = exercises
    payload["performedAt"] = datetime.now(UTC).isoformat()
    response = client.post("/sessions/gym", json=payload, headers=headers)
    assert response.status_code == 201, response.text


def test_week_feedback_points_to_main_gap(client: TestClient, seed_catalog) -> None:
    headers = _headers(client, "weekfb@example.com")
    empty = client.get("/analysis/week-feedback", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["focusCode"] is None

    _gym_session(client, headers, ["press banca", "press militar"])
    data = client.get("/analysis/week-feedback", headers=headers).json()
    assert data["focusCode"].startswith("pattern:")
    assert "próximo entreno" in data["message"]
    assert data["headline"]


def test_routine_analysis_reports_adherence(client: TestClient, seed_catalog) -> None:
    headers = _headers(client, "adherence@example.com")
    ids = _ids(client, headers)
    routine = {"name": "Plan", "days": [_day(1, [ids["press banca"], ids["press militar"]])]}
    created = client.post("/routines", json=routine, headers=headers).json()
    # Hace press banca y algo fuera de la rutina; se salta el press militar.
    _gym_session(client, headers, ["press banca", "fondos en paralelas"])

    data = client.get(f"/analysis/sport?routineId={created['id']}", headers=headers).json()
    adherence = data["adherence"]
    assert adherence["sessions"] == 1
    assert 0 < adherence["pct"] < 100
    assert any("militar" in e["name"].lower() for e in adherence["skipped"])
    assert any("fondos" in e["name"].lower() for e in adherence["offPlan"])
    assert adherence["historyScore"] is not None
