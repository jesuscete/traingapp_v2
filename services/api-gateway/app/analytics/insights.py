"""Avisos deterministas para la pantalla de inicio (sin IA): constancia, fatiga, carga,
nutrición y peso. Cada regla es una función pura sobre `InsightFacts`."""

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

from app.analytics.sport_analysis import GROUP_LABELS

InsightKind = Literal["good", "warning", "rest", "tip"]
PRIORITY: dict[InsightKind, int] = {"rest": 0, "warning": 1, "tip": 2, "good": 3}

INACTIVE_DAYS = 4
LOAD_JUMP_RATIO = 1.5
LOAD_JUMP_MIN_PREV = 60
PROTEIN_SHORT_RATIO = 0.7
EVENING_HOUR = 18
MEALS_EXPECTED_HOUR = 14
WEIGHT_TREND_KG = 0.2
GOOD_WEEK_SESSIONS = 3


@dataclass(frozen=True)
class Insight:
    kind: InsightKind
    title: str
    detail: str
    href: str | None = None


@dataclass(frozen=True)
class InsightFacts:
    today: date
    session_dates: list[date]
    week_minutes: int = 0
    prev_week_minutes: int = 0
    tired_groups: list[str] = field(default_factory=list)
    overloaded_groups: list[str] = field(default_factory=list)
    meals_today: int = 0
    protein_g: float = 0
    protein_target_g: float | None = None
    goal: str = "mantener"
    weight_change_week_kg: float | None = None
    hour: int | None = None


def _names(groups: list[str], limit: int = 3) -> str:
    return ", ".join(GROUP_LABELS.get(g, g) for g in groups[:limit])


def days_since_last(facts: InsightFacts) -> int | None:
    past = [d for d in facts.session_dates if d <= facts.today]
    return (facts.today - max(past)).days if past else None


def sessions_last_week(facts: InsightFacts) -> int:
    since = facts.today - timedelta(days=6)
    return sum(1 for d in facts.session_dates if since <= d <= facts.today)


def _consistency(facts: InsightFacts) -> list[Insight]:
    gap = days_since_last(facts)
    if gap is None:
        return [
            Insight(
                "tip",
                "Registra tu primer entreno",
                "Con unos pocos registros empezarás a ver fatiga, carga y progreso.",
                "/entrenar",
            )
        ]
    if gap >= INACTIVE_DAYS:
        return [
            Insight(
                "warning",
                f"Llevas {gap} días sin registrar",
                "Si has entrenado, regístralo o importa la actividad del reloj.",
                "/entrenar",
            )
        ]
    return []


def _fatigue(facts: InsightFacts) -> list[Insight]:
    out: list[Insight] = []
    if facts.tired_groups:
        out.append(
            Insight(
                "rest",
                f"Descansa {_names(facts.tired_groups)}",
                "Fatiga alta: mejor trabajo suave u otra zona del cuerpo hoy.",
                "/progreso?tab=fatiga",
            )
        )
    if facts.overloaded_groups:
        out.append(
            Insight(
                "warning",
                "Te estás cargando mucho",
                f"{_names(facts.overloaded_groups).capitalize()}: carga semanal muy por encima "
                "de tu media del mes.",
                "/progreso?tab=fatiga",
            )
        )
    elif (
        facts.prev_week_minutes >= LOAD_JUMP_MIN_PREV
        and facts.week_minutes > facts.prev_week_minutes * LOAD_JUMP_RATIO
    ):
        out.append(
            Insight(
                "warning",
                "Subida brusca de volumen",
                f"{facts.week_minutes} min esta semana frente a {facts.prev_week_minutes} la "
                "anterior. Sube de forma progresiva.",
                "/progreso",
            )
        )
    return out


def _nutrition(facts: InsightFacts) -> list[Insight]:
    if facts.hour is None:
        return []
    if facts.meals_today == 0 and facts.hour >= MEALS_EXPECTED_HOUR:
        return [
            Insight("tip", "Sin comidas registradas hoy", "Añade lo que has comido.", "/comidas")
        ]
    target = facts.protein_target_g
    if (
        target
        and facts.meals_today
        and facts.hour >= EVENING_HOUR
        and facts.protein_g < target * PROTEIN_SHORT_RATIO
    ):
        missing = round(target - facts.protein_g)
        return [
            Insight(
                "tip",
                f"Te faltan {missing} g de proteína",
                "Inclúyela en la cena para recuperar mejor.",
                "/comidas",
            )
        ]
    return []


def _weight(facts: InsightFacts) -> list[Insight]:
    change = facts.weight_change_week_kg
    if change is None:
        return []
    losing_goal = facts.goal in ("perder", "corte")
    if losing_goal and change > WEIGHT_TREND_KG:
        return [
            Insight(
                "tip",
                f"Peso +{change:.1f} kg esta semana",
                "Tu objetivo es bajar: revisa las calorías de los últimos días.",
                "/comidas?tab=peso",
            )
        ]
    if facts.goal == "ganar" and change < -WEIGHT_TREND_KG:
        return [
            Insight(
                "tip",
                f"Peso {change:.1f} kg esta semana",
                "Para ganar masa necesitas comer algo más.",
                "/comidas?tab=peso",
            )
        ]
    return []


def build_insights(facts: InsightFacts) -> list[Insight]:
    insights = [
        *_consistency(facts),
        *_fatigue(facts),
        *_nutrition(facts),
        *_weight(facts),
    ]
    alerts = [i for i in insights if i.kind in ("rest", "warning")]
    week = sessions_last_week(facts)
    if not alerts and week >= GOOD_WEEK_SESSIONS:
        insights.append(
            Insight(
                "good", "Vas bien", f"{week} sesiones en los últimos 7 días y carga controlada."
            )
        )
    elif not insights:
        insights.append(Insight("good", "Todo en orden", "Sin avisos de fatiga ni de carga."))
    return sorted(insights, key=lambda i: PRIORITY[i.kind])
