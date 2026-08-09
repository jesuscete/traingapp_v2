from app.analytics.impacts import compute_muscle_impacts
from app.models.training import Exercise


def _exercise(
    name: str, sets: int | None = None, reps: int | None = None, weight_kg: float | None = None
) -> Exercise:
    return Exercise(name=name, sets=sets, reps=reps, weight_kg=weight_kg)


def test_catalog_multi_muscle_normalized() -> None:
    exercise = _exercise("press banca", sets=5, reps=5, weight_kg=80)
    exercise.volume_kg = 2000.0
    catalog = {"press banca": {"chest": 0.6, "triceps": 0.3, "shoulders": 0.1}}

    impacts = compute_muscle_impacts([exercise], catalog)

    assert impacts[0].muscle_group == "chest"
    assert impacts[0].activation == 1.0
    by_group = {item.muscle_group: item.activation for item in impacts}
    assert by_group["triceps"] == 0.5
    assert by_group["shoulders"] == 0.167


def test_catalog_aggregates_two_exercises() -> None:
    chest = _exercise("press banca", sets=5, reps=5, weight_kg=80)
    chest.volume_kg = 2000.0
    curls = _exercise("curl biceps", sets=3, reps=10, weight_kg=20)
    curls.volume_kg = 600.0
    catalog = {
        "press banca": {"chest": 0.6, "triceps": 0.3, "shoulders": 0.1},
        "curl biceps": {"biceps": 0.8, "forearms": 0.2},
    }

    impacts = compute_muscle_impacts([chest, curls], catalog)

    by_group = {item.muscle_group: item.activation for item in impacts}
    assert by_group["chest"] == 1.0
    assert by_group["biceps"] == 0.4
    assert by_group["forearms"] == 0.1
    assert by_group["triceps"] == 0.5


def test_unknown_exercise_uses_heuristic_fallback() -> None:
    exercise = _exercise("press banca raro", sets=3, reps=10, weight_kg=100)
    exercise.volume_kg = 3000.0

    impacts = compute_muscle_impacts([exercise], {})

    assert impacts[0].muscle_group == "chest"


def test_legs_fallback_maps_to_leg_muscles() -> None:
    exercise = _exercise("sentadilla zancada", sets=4, reps=8, weight_kg=60)
    exercise.volume_kg = 1920.0

    impacts = compute_muscle_impacts([exercise], {})

    groups = {item.muscle_group for item in impacts}
    assert groups == {"quadriceps", "hamstrings", "glutes", "calves"}
    by_group = {item.muscle_group: item.activation for item in impacts}
    assert by_group["quadriceps"] == 1.0


def test_no_match_returns_empty() -> None:
    exercise = _exercise("ejercicio totalmente desconocido", sets=3, reps=10)
    exercise.volume_kg = 0.0

    impacts = compute_muscle_impacts([exercise], {})

    assert impacts == []
