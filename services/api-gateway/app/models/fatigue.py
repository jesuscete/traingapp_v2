import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DisciplineMuscleLoad(Base):
    """Catalogo de carga por disciplina y grupo muscular (N_g en [0, 1]).

    Fuente de verdad de las ponderaciones en runtime. Sembrada por migracion
    desde `app.analytics.fatigue.MUSCLE_LOAD_DEFAULT` y editable por admin.
    """

    __tablename__ = "discipline_muscle_load"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    discipline: Mapped[str] = mapped_column(String(40), index=True)
    muscle_group: Mapped[str] = mapped_column(String(40))
    load: Mapped[float] = mapped_column(Float)

    __table_args__ = (
        UniqueConstraint(
            "discipline", "muscle_group", name="uq_discipline_muscle_group"
        ),
    )


class DailyReadiness(Base):
    """Readiness diaria del usuario (sueno, DOMS, descanso; HRV/nutricion futuras)."""

    __tablename__ = "daily_readiness"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    doms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rest_day: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_user_readiness_date"),)
