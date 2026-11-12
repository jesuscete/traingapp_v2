from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient

from app.analytics.insights import InsightFacts, build_insights

TODAY = date(2026, 11, 12)


def _kinds(facts: InsightFacts) -> list[tuple[str, str]]:
    return [(i.kind, i.title) for i in build_insights(facts)]


def test_inactivity_and_first_session() -> None:
    assert _kinds(InsightFacts(today=TODAY, session_dates=[]))[0][1] == "Registra tu primer entreno"
    idle = _kinds(InsightFacts(today=TODAY, session_dates=[TODAY - timedelta(days=5)]))
    assert idle[0] == ("warning", "Llevas 5 días sin registrar")


def test_rest_comes_first_and_hides_good_week() -> None:
    dates = [TODAY - timedelta(days=d) for d in range(4)]
    good = _kinds(InsightFacts(today=TODAY, session_dates=dates))
    assert good == [("good", "Vas bien")]
    tired = build_insights(
        InsightFacts(
            today=TODAY,
            session_dates=dates,
            tired_groups=["quadriceps"],
            overloaded_groups=["back"],
        )
    )
    assert [i.kind for i in tired] == ["rest", "warning"]
    assert "cuádriceps" in tired[0].title


def test_load_jump_nutrition_and_weight_tips() -> None:
    facts = InsightFacts(
        today=TODAY,
        session_dates=[TODAY],
        week_minutes=300,
        prev_week_minutes=120,
        meals_today=2,
        protein_g=60,
        protein_target_g=150,
        goal="corte",
        weight_change_week_kg=0.5,
        hour=20,
    )
    titles = [t for _, t in _kinds(facts)]
    assert "Subida brusca de volumen" in titles
    assert "Te faltan 90 g de proteína" in titles
    assert "Peso +0.5 kg esta semana" in titles
    no_meals = InsightFacts(today=TODAY, session_dates=[TODAY], hour=15)
    assert ("tip", "Sin comidas registradas hoy") in _kinds(no_meals)
    assert all(
        t != "Sin comidas registradas hoy"
        for _, t in _kinds(InsightFacts(today=TODAY, session_dates=[TODAY]))
    )


def test_home_endpoint_summarises_week_by_sport(client: TestClient) -> None:
    body = {"email": "home@example.com", "password": "password123", "name": "H"}
    token = client.post("/auth/register", json=body).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    now = datetime.now(UTC)
    for days_ago, discipline, minutes in (
        (1, "running", 40),
        (2, "running", 30),
        (3, "boxing", 60),
    ):
        client.post(
            "/sessions",
            json={
                "discipline": discipline,
                "rawText": discipline,
                "durationMinutes": minutes,
                "performedAt": (now - timedelta(days=days_ago)).isoformat(),
            },
            headers=headers,
        )
    home = client.get("/stats/home", params={"hour": 10}, headers=headers).json()
    assert home["weekSessions"] == 3 and home["weekMinutes"] == 130
    assert home["weekBySport"][0] == {
        "discipline": "running",
        "sessions": 2,
        "minutes": 70,
        "distanceM": 0,
    }
    assert home["daysSinceLast"] == 1 and len(home["activeDays"]) == 3
    assert home["insights"] and {"kind", "title", "detail", "href"} <= home["insights"][0].keys()
