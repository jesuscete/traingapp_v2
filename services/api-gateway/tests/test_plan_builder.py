"""Generador de planes por árbol de decisión (sin IA) con el catálogo real."""

import uuid
from functools import lru_cache
from pathlib import Path

from fastapi.testclient import TestClient

from app.analytics.catalog_seed import load_free_exercise_db
from app.analytics.exercise_seed import EXERCISE_CATALOG_SEED
from app.analytics.sport_analysis import analyze
from app.models import ExerciseCatalog
from app.services import plan_builder, plan_repair, sport_registry
from app.services.sport_analysis import CatalogItem, catalog_item

DATA = Path(__file__).resolve().parents[1] / "data"
LEG_PATTERNS = {"sentadilla", "bisagra", "unilateral"}


@lru_cache(maxsize=1)
def _catalog() -> list[CatalogItem]:
    rows = [
        ExerciseCatalog(
            id=uuid.uuid4(),
            name=str(e["name"]),
            normalized_name=str(e["normalized_name"]),
            exercise_type="gym",
            muscle_map=e["muscles"],
            images=[],
            details=None,
        )
        for e in EXERCISE_CATALOG_SEED
    ]
    for r in load_free_exercise_db(DATA / "exercises.json"):
        rows.append(
            ExerciseCatalog(
                id=uuid.uuid4(),
                name=r["name"],
                normalized_name=r["normalized_name"],
                exercise_type="gym",
                muscle_map=r["muscle_map"],
                images=r["images"],
                details=r["details"],
            )
        )
    return [catalog_item(r) for r in rows]


def _build(req: plan_builder.PlanRequest, sport: str) -> plan_builder.BuiltPlan:
    return plan_builder.build_plan(
        req, _catalog(), sport_registry.profile_doc(sport), sport_registry.profile_doc("generic")
    )


def _gym_days(built: plan_builder.BuiltPlan) -> list[dict]:
    return [d for d in built.data["days"] if d["dayType"] == "gimnasio"]  # type: ignore[union-attr]


def _patterns(day: dict) -> set[str]:
    by_name = {c.name: c for c in _catalog()}
    return {p for e in day["exercises"] for p in by_name[e["name"]].patterns}


BOXING = plan_builder.PlanRequest(
    sports=[("boxeo", [1, 3], 60)], gym_days=3, split=None, performance=True, level="intermediate"
)


def test_boxing_plan_respects_sport_days_and_load_rules() -> None:
    built = _build(BOXING, "boxing")
    gym = _gym_days(built)
    assert len(gym) == 3
    assert {d["dayOfWeek"] for d in gym}.isdisjoint({1, 3})
    for day in gym:
        assert 3 <= len(day["exercises"]) <= plan_builder.MAX_EXERCISES_PER_DAY
        if (day["dayOfWeek"] % 7) + 1 in {1, 3}:
            assert not _patterns(day) & LEG_PATTERNS, day  # nada de pierna la víspera
    all_patterns = set().union(*(_patterns(d) for d in gym))
    assert {"pliometria", "rotacion", "cuello"} <= all_patterns
    sport_days = [d for d in built.data["days"] if d["dayType"] == "deporte"]  # type: ignore[union-attr]
    assert [d["dayOfWeek"] for d in sport_days] == [1, 3]


def test_explosive_work_goes_first_in_the_session() -> None:
    by_name = {c.name: c for c in _catalog()}
    for day in _gym_days(_build(BOXING, "boxing")):
        patterns = [by_name[e["name"]].patterns for e in day["exercises"]]
        explosive = [i for i, p in enumerate(patterns) if p & set(plan_builder.EXPLOSIVE)]
        if explosive:
            assert explosive[0] == 0


def test_boxing_plan_scores_well_against_the_profile() -> None:
    built = _build(BOXING, "boxing")
    # Mismo camino que el asistente: formato de plan -> análisis del deporte.
    from app.schemas.plan import PlanDayOut, PlanExerciseOut, PlanSetTargetOut, PlanSummaryOut

    by_name = {c.name: c for c in _catalog()}
    days = []
    for d in built.data["days"]:  # type: ignore[union-attr]
        exercises = [
            PlanExerciseOut(
                name=e["name"],
                exercise_id=by_name[e["name"]].row.id,
                sets=[
                    PlanSetTargetOut(
                        target_reps_min=s["targetRepsMin"], target_reps_max=s["targetRepsMax"]
                    )
                    for s in e["sets"]
                ],
            )
            for e in d.get("exercises", [])
        ]
        days.append(
            PlanDayOut(day_of_week=d["dayOfWeek"], day_type=d["dayType"], exercises=exercises)
        )
    work, sport_days = plan_repair.plan_work(
        PlanSummaryOut(name="x", days=days), {c.row.id: c for c in _catalog()}
    )
    score = analyze(
        work, sport_registry.sport_profile("boxing"), weeks=1, sport_days=sport_days
    ).score
    assert score >= 60, score


def test_bodyweight_only_plan_uses_only_bodyweight_exercises() -> None:
    req = plan_builder.PlanRequest(
        sports=[], gym_days=3, split=None, performance=False, allowed=frozenset({"body only"})
    )
    # El catálogo puede repetir nombre en español: basta con que exista la versión sin material.
    bodyweight_names = {c.name for c in _catalog() if c.equipment == "body only"}
    gym = _gym_days(_build(req, "generic"))
    assert gym and all(e["name"] in bodyweight_names for d in gym for e in d["exercises"])


def test_gym_days_are_capped_by_free_days() -> None:
    req = plan_builder.PlanRequest(
        sports=[("correr", [1, 2, 3, 4, 5], 45)], gym_days=4, split=None, performance=True
    )
    built = _build(req, "triathlon")
    assert len(_gym_days(built)) == 2
    assert "días libres" in built.notes[0]


def test_split_choice_is_honoured() -> None:
    req = plan_builder.PlanRequest(sports=[], gym_days=3, split="push_pull", performance=False)
    labels = [d["label"] for d in _gym_days(_build(req, "generic"))]
    assert labels == ["Empuje", "Tirón", "Pierna"]


def _auth_headers(client: TestClient, email: str) -> dict[str, str]:
    body = {"email": email, "password": "password123", "name": "Plan"}
    token = client.post("/auth/register", json=body).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_guided_plan_flow_builds_without_ai(
    client: TestClient, seed_catalog, seed_disciplines, _block_real_llm: list[str]
) -> None:
    headers = _auth_headers(client, "plan-rules@example.com")
    for text in ("quiero crear una rutina", "boxeo", "lunes y miércoles", "1 hora", "boxeo", "3"):
        client.post("/chat/draft", json={"text": text}, headers=headers)
    ready = client.post("/chat/draft", json={"text": "me da igual"}, headers=headers)
    assert ready.status_code == 200, ready.text
    data = ready.json()
    assert data["planStatus"] == "ready", data
    gym = [d for d in data["plan"]["days"] if d["dayType"] == "gimnasio"]
    assert len(gym) == 3 and all(d["exercises"] for d in gym)
    assert "mapa de boxeo" in data["message"]
    assert _block_real_llm == []
