from app.schemas.session import CamelModel, SessionListItem


class DisciplineStatOut(CamelModel):
    discipline: str
    sessions: int
    duration_minutes: int
    volume_kg: float
    estimated_kcal: float


class DisciplineDeltaOut(CamelModel):
    discipline: str
    sessions: int
    delta_pct: float | None


class HighlightsOut(CamelModel):
    total_sessions: int
    total_duration_minutes: int
    total_volume_kg: float
    total_kcal: float


class HistorySummaryOut(CamelModel):
    days: int
    highlights: HighlightsOut
    by_discipline: list[DisciplineStatOut]
    deltas: list[DisciplineDeltaOut]
    recent: list[SessionListItem]


class SessionPageOut(CamelModel):
    items: list[SessionListItem]
    total: int
    page: int
    page_size: int
    has_more: bool
