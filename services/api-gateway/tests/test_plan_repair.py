import uuid

from app.analytics.sport_analysis import Status, _zone_credit
from app.models import ExerciseCatalog
from app.schemas.plan import PlanDayOut, PlanExerciseOut, PlanSetTargetOut, PlanSummaryOut
from app.services.plan_repair import complete_plan, plan_work
from app.services.sport_analysis import catalog_item
from app.services.sport_registry import sport_profile

BOXING = sport_profile("boxing")


def _row(name: str, muscles: dict[str, float], **details: str) -> ExerciseCatalog:
    return ExerciseCatalog(
        id=uuid.uuid4(),
        name=name,
        normalized_name=name.lower(),
        owner_user_id=None,
        exercise_type="strength",
        muscle_map=muscles,
        details=details,
        images=["x.jpg"],
    )


CATALOG = [
    catalog_item(r)
    for r in [
        _row("Bench Press", {"chest": 1, "triceps": 0.5}, force="push"),
        _row("Squat", {"quadriceps": 1, "glutes": 0.6}),
        _row("Russian Twist", {"core": 1}),
        _row("Pallof Press", {"core": 1}),
        _row("Box Jump", {"quadriceps": 0.8, "calves": 0.6}, category="plyometrics"),
        _row("Power Clean", {"quadriceps": 0.6, "glutes": 0.6, "back": 0.6}),
        _row("Bulgarian Split Squat", {"quadriceps": 1, "glutes": 0.6}),
        _row("Romanian Deadlift", {"hamstrings": 1, "glutes": 0.6}),
        _row("Neck Flexion", {"neck": 1}),
        _row("Barbell Row", {"back": 1, "biceps": 0.4}, force="pull"),
        _row("Pull Up", {"back": 1, "biceps": 0.5}, force="pull"),
    ]
]
BY_NAME = {c.row.name: c for c in CATALOG}


def _ex(name: str, sets: int = 3, reps: tuple[int, int] = (6, 8)) -> PlanExerciseOut:
    item = BY_NAME[name]
    return PlanExerciseOut(
        name=item.name,
        exercise_id=item.row.id,
        sets=[PlanSetTargetOut(target_reps_min=reps[0], target_reps_max=reps[1])] * sets,
    )


def _plan(*gym_days: list[PlanExerciseOut]) -> PlanSummaryOut:
    days = [
        PlanDayOut(day_of_week=1 + 2 * i, day_type="gimnasio", exercises=list(ex))
        for i, ex in enumerate(gym_days)
    ]
    days.append(PlanDayOut(day_of_week=2, day_type="deporte", discipline_name="Boxeo"))
    return PlanSummaryOut(name="Plan", days=days)


def test_complete_plan_fills_missing_patterns_and_raises_score() -> None:
    plan = _plan([_ex("Bench Press"), _ex("Squat")], [_ex("Barbell Row")])
    result = complete_plan(plan, BOXING, CATALOG)

    assert result.score_after > result.score_before
    assert result.added, "debería añadir ejercicios para los patrones ausentes"
    assert "Russian Twist" in result.added  # potencia rotacional, ausente en el plan
    assert result.score_after >= 65
    # El plan original no se modifica.
    assert sum(len(d.exercises) for d in plan.days) == 3
    # Lo añadido se reparte: ningún día supera el máximo.
    assert all(len(d.exercises) <= 8 for d in result.plan.days)


def test_complete_plan_keeps_good_plan_untouched() -> None:
    plan = _plan(
        [
            _ex("Russian Twist", 3),
            _ex("Box Jump", 3, (3, 5)),
            _ex("Power Clean", 3, (3, 5)),
            _ex("Bulgarian Split Squat", 3),
            _ex("Barbell Row", 3),
            _ex("Neck Flexion", 2, (12, 15)),
        ],
        [
            _ex("Russian Twist", 3),
            _ex("Pallof Press", 4, (8, 12)),
            _ex("Box Jump", 3, (3, 5)),
            _ex("Romanian Deadlift", 4),
            _ex("Pull Up", 4),
            _ex("Bulgarian Split Squat", 3),
            _ex("Barbell Row", 3),
            _ex("Neck Flexion", 2, (12, 15)),
        ],
    )
    result = complete_plan(plan, BOXING, CATALOG, target=0)
    assert result.added == []
    assert result.score_after == result.score_before


def test_plan_work_skips_sport_days() -> None:
    work, sport_days = plan_work(_plan([_ex("Squat")]), {c.row.id: c for c in CATALOG})
    assert sport_days == {2}
    assert len(work) == 1 and work[0].reps == [7, 7, 7]


def test_zone_credit_is_partial() -> None:
    assert _zone_credit(Status(0.4, 0.3, 0.55, "ok")) == 1.0
    assert 0 < _zone_credit(Status(0.2, 0.3, 0.55, "low")) < 1
    assert _zone_credit(Status(0.0, 0.3, 0.55, "missing")) == 0.0
