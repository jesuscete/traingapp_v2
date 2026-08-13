import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.routine import Discipline


class DisciplineMuscleLoad(Base):
    """Catalogo de carga por disciplina y grupo muscular (N_g en [0, 1]).

    Fuente de verdad de las ponderaciones en runtime. Sembrada por migracion
    desde `app.analytics.fatigue.MUSCLE_LOAD_DEFAULT` y editable por admin.
    `discipline_id` referencia el catalogo canonical `discipline`.
    """

    __tablename__ = "discipline_muscle_load"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    discipline_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("discipline.id", ondelete="CASCADE"),
        index=True,
    )
    muscle_group: Mapped[str] = mapped_column(String(40))
    load: Mapped[float] = mapped_column(Float)

    discipline: Mapped["Discipline"] = relationship(back_populates="muscle_loads")

    __table_args__ = (
        UniqueConstraint(
            "discipline_id", "muscle_group", name="uq_discipline_muscle_group"
        ),
    )


class DailyReadiness(Base):
    """Readiness diaria del usuario (sueño, DOMS global, descanso; HRV/nutrición).

    `hrv_score` (0-1 percentil semanal) y `resting_hr` alimentan la proyección
    futura de recuperación (ADR-013). El DOMS localizado por grupo vive en
    `DailyMuscleDoms` (ADR-011).
    """

    __tablename__ = "daily_readiness"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    doms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rest_day: Mapped[bool] = mapped_column(Boolean, default=False)
    hrv_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    resting_hr: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (UniqueConstraint("user_id", "date", name="uq_user_readiness_date"),)


class DailyMuscleDoms(Base):
    """DOMS localizado por grupo muscular (0-10) para un día (mapa corporal).

    Alimenta el modulador de recuperación por grupo (ADR-011): penaliza la
    recuperación del grupo con dolor reportado.
    """

    __tablename__ = "daily_muscle_doms"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    date: Mapped[date] = mapped_column(Date)
    muscle_group: Mapped[str] = mapped_column(String(40))
    pain: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "date", "muscle_group", name="uq_user_date_muscle_group"
        ),
    )


class UserMuscleCalibration(Base):
    """Calibracion personal del modelo de fatiga (spec 7.3, ADR-015).

    El DOMS reportado por el usuario corrige la ponderacion `N_g` y la
    velocidad de recuperacion del dano (`tau2`) de cada grupo. `ng_delta` es
    la correccion aditiva acotada (ej. +0.15) y `tau2_factor` el multiplicador
    de `tau2` (1.0 = neutro, >1 recuperacion mas lenta).
    """

    __tablename__ = "user_muscle_calibration"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    muscle_group: Mapped[str] = mapped_column(String(40))
    ng_delta: Mapped[float] = mapped_column(Float, default=0.0)
    tau2_factor: Mapped[float] = mapped_column(Float, default=1.0)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    pearson_r: Mapped[float | None] = mapped_column(Float, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "muscle_group", name="uq_user_calibration_muscle_group"
        ),
    )
