"""Modelo jerárquico de entrenamiento de gimnasio (4 niveles).

workout_session (training_sessions) -> workout_exercise -> set -> set_entry.
`workout_session_summary` es la tabla resumen materializada, recalculada al
cerrar/confirmar el entreno (ADR-0xx).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.training import TrainingSession


class WorkoutExercise(Base):
    __tablename__ = "workout_exercise"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("training_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    exercise_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("exercise_catalog.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120))
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    superset_group_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    volume_kg: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    sets: Mapped[list["WorkoutSet"]] = relationship(
        back_populates="workout_exercise",
        cascade="all, delete-orphan",
        order_by="WorkoutSet.set_number",
    )
    session: Mapped["TrainingSession"] = relationship(back_populates="workout_exercises")


class WorkoutSet(Base):
    __tablename__ = "set"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workout_exercise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("workout_exercise.id", ondelete="CASCADE"),
        index=True,
    )
    set_number: Mapped[int] = mapped_column(Integer)
    set_type: Mapped[str] = mapped_column(String(16), default="normal")
    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_warmup: Mapped[bool] = mapped_column(Boolean, default=False)
    volume_kg: Mapped[float] = mapped_column(Float, default=0)

    workout_exercise: Mapped[WorkoutExercise] = relationship(
        back_populates="sets"
    )
    entries: Mapped[list["SetEntry"]] = relationship(
        back_populates="workout_set",
        cascade="all, delete-orphan",
        order_by="SetEntry.entry_order",
    )


class SetEntry(Base):
    __tablename__ = "set_entry"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    set_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("set.id", ondelete="CASCADE"),
        index=True,
    )
    entry_order: Mapped[int] = mapped_column(Integer)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    weight_unit: Mapped[str] = mapped_column(String(3), default="kg")
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    distance_meters: Mapped[float | None] = mapped_column(Float, nullable=True)
    rpe: Mapped[int | None] = mapped_column(Integer, nullable=True)
    side: Mapped[str] = mapped_column(String(8), default="both")

    workout_set: Mapped[WorkoutSet] = relationship(back_populates="entries")


class WorkoutSessionSummary(Base):
    __tablename__ = "workout_session_summary"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("training_sessions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    total_volume: Mapped[float] = mapped_column(Float, default=0)
    avg_rpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    sets_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_min: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    session: Mapped["TrainingSession"] = relationship(back_populates="summary")
