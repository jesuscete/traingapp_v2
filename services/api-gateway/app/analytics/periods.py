"""Calculo de periodos equivalentes y comparaciones de actividad por periodo.

Funciones puras y aisladas para la pantalla de historial de entrenos:
- ``previous_period``: ventana anterior de la misma duracion (Capa 1, progresion).
- ``discipline_totals``: agregacion de sesiones por disciplina.
- ``compute_discipline_deltas``: variacion % de cada disciplina entre dos periodos.
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.models import TrainingSession


@dataclass
class DisciplineTotals:
    discipline: str
    sessions: int
    duration_minutes: int
    volume_kg: float
    estimated_kcal: float


@dataclass
class DisciplineDelta:
    discipline: str
    sessions: int
    delta_pct: float | None


def previous_period(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    """Devuelve el periodo inmediatamente anterior de la misma duracion.

    ``(start, end)`` define el periodo actual (half-open: [start, end)).
    Devuelve ``(start - delta, start)`` con ``delta = end - start``.
    """
    delta = end - start
    return start - delta, start


def discipline_totals(
    sessions: list[TrainingSession],
) -> list[DisciplineTotals]:
    """Agrega sesiones por disciplina (contador, duracion, volumen, kcal)."""
    count: dict[str, int] = defaultdict(int)
    duration: dict[str, int] = defaultdict(int)
    volume: dict[str, float] = defaultdict(float)
    kcal: dict[str, float] = defaultdict(float)
    for ts in sessions:
        count[ts.discipline] += 1
        duration[ts.discipline] += ts.duration_minutes or 0
        volume[ts.discipline] += ts.volume_kg or 0
        kcal[ts.discipline] += ts.estimated_kcal or 0
    return [
        DisciplineTotals(
            discipline=name,
            sessions=count[name],
            duration_minutes=duration[name],
            volume_kg=round(volume[name], 1),
            estimated_kcal=round(kcal[name], 1),
        )
        for name in sorted(count)
    ]


def _pct_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


def compute_discipline_deltas(
    current: list[TrainingSession],
    previous: list[TrainingSession],
    *,
    top_n: int = 3,
) -> list[DisciplineDelta]:
    """Variacion % de sesiones por disciplina (actual vs. periodo anterior).

    Devuelve los ``top_n`` con mayor variacion absoluta. Solo incluye
    disciplinas presentes en alguno de los dos periodos.
    """
    current_count = _sessions_by_discipline(current)
    previous_count = _sessions_by_discipline(previous)

    deltas: list[DisciplineDelta] = []
    for discipline in sorted(set(current_count) | set(previous_count)):
        cur = current_count.get(discipline, 0)
        prev = previous_count.get(discipline, 0)
        deltas.append(
            DisciplineDelta(
                discipline=discipline,
                sessions=cur,
                delta_pct=_pct_change(cur, prev),
            )
        )

    deltas.sort(
        key=lambda item: abs(item.delta_pct) if item.delta_pct is not None else 0,
        reverse=True,
    )
    return deltas[:top_n]


def _sessions_by_discipline(sessions: list[TrainingSession]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for ts in sessions:
        counts[ts.discipline] += 1
    return counts


def period_range(days: int, now: datetime | None = None) -> tuple[datetime, datetime]:
    """Rango (start, end) para los ultimos ``days`` dias (half-open [start, end))."""
    end = now or datetime.now(UTC)
    return end - timedelta(days=days), end
