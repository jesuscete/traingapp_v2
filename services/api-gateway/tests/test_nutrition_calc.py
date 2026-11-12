from datetime import date

from app.analytics.nutrition import bmr_mifflin, daily_target, goal_rate_kg_week, weight_trend

TODAY = date(2026, 11, 12)
BASE = dict(
    weight_kg=75,
    height_cm=178,
    age=32,
    sex="male",
    activity_factor=1.4,
    protein_g_per_kg=2.0,
    today=TODAY,
)


def test_mifflin_reference_values() -> None:
    # 10*75 + 6.25*178 - 5*32 + 5 = 1707.5
    assert bmr_mifflin(75, 178, 32, "male") == 1707.5
    assert bmr_mifflin(75, 178, 32, "female") == 1541.5
    assert bmr_mifflin(75, 178, 32, None) == 1624.5


def test_maintenance_includes_real_training_kcal() -> None:
    rest = daily_target(**BASE, training_kcal=0, goal="mantener")
    training = daily_target(**BASE, training_kcal=600, goal="mantener")
    assert training.target_kcal - rest.target_kcal == 600
    assert rest.target_kcal == round(1707.5 * 1.4)
    assert rest.protein_g == 150


def test_macros_add_up_to_target() -> None:
    t = daily_target(**BASE, training_kcal=400, goal="mantener")
    assert abs(t.protein_g * 4 + t.fat_g * 9 + t.carbs_g * 4 - t.target_kcal) <= 12
    assert t.fat_g >= 0.8 * 75


def test_cut_towards_weight_class_and_safety_cap() -> None:
    # 75 -> 72 kg en 6 semanas = 0,5 kg/semana (por debajo del 1 %)
    rate, notes = goal_rate_kg_week(
        "corte",
        75,
        rate_kg_week=None,
        target_weight_kg=72,
        target_date=date(2026, 12, 24),
        today=TODAY,
    )
    assert rate == -0.5 and notes == []
    # 75 -> 69 en 2 semanas: 3 kg/semana -> se limita a 0,75 (1 % de 75) y avisa
    fast, warning = goal_rate_kg_week(
        "corte",
        75,
        rate_kg_week=None,
        target_weight_kg=69,
        target_date=date(2026, 11, 26),
        today=TODAY,
    )
    assert fast == -0.75 and "1 %" in warning[0]
    cut = daily_target(
        **BASE, training_kcal=0, goal="corte", target_weight_kg=72, target_date=date(2026, 12, 24)
    )
    assert cut.adjustment_kcal == -550  # 0,5 kg x 7700 / 7


def test_target_never_below_bmr() -> None:
    t = daily_target(
        **{**BASE, "activity_factor": 1.0}, training_kcal=0, goal="perder", rate_kg_week=1.0
    )
    assert t.target_kcal >= t.bmr
    assert t.notes


def test_weight_trend_moving_average() -> None:
    points = [(date(2026, 11, d), 76.0) for d in range(1, 6)] + [
        (date(2026, 11, d), 75.0) for d in range(6, 13)
    ]
    trend = weight_trend(points, TODAY)
    assert trend.latest_kg == 75.0
    assert trend.average_7d_kg == 75.0
    assert trend.change_week_kg == -1.0  # 75 (últimos 7 días) frente a 76 (7-13 días antes)
    assert weight_trend([], TODAY).latest_kg is None
