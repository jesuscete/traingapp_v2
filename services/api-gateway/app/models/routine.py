"""Modelo de plantilla recurrente (rutina): lo que planeas hacer.

Separado de la sesion real (`training_sessions`). La rutina es un plan
semanal sin pesos:

    routine -> routine_day -> routine_exercise -> routine_set

`routine_set` es el equivalente de la tabla `set` ya existente pero SIN
ningun campo de peso: es un objetivo, no un resultado. `discipline` es el
catalogo de disciplinas (boxeo, running, ciclismo...), fuente de verdad que
sustituye al antiguo enum `Discipline`.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.fatigue import DisciplineMuscleLoad


class Discipline(Base):
    """Catalogo de disciplinas de entrenamiento (sustituye al enum).

    name: nombre visible (ej. "Boxeo"). normalized_name: clave unica
    (minusculas, sin acentos). met: valor MET (kcal por hora por kg de peso).
    category: tipo de deporte (gimnasio, combate, equipo, raqueta...).
    kind: tratamiento analitico: "gym" (trabajo mecanico) o "cardio" (MET).
    """

    __tablename__ = "discipline"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(80))
    normalized_name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    met: Mapped[float] = mapped_column(Float, default=4.0)
    category: Mapped[str] = mapped_column(String(30), default="otros")
    kind: Mapped[str] = mapped_column(String(10), default="cardio")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    muscle_loads: Mapped[list["DisciplineMuscleLoad"]] = relationship(
        back_populates="discipline",
        cascade="all, delete-orphan",
    )


class Routine(Base):
    __tablename__ = "routine"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    days: Mapped[list["RoutineDay"]] = relationship(
        back_populates="routine",
        cascade="all, delete-orphan",
        order_by="RoutineDay.day_of_week",
    )

    __table_args__ = (
        # Una sola rutina activa por usuario.
        Index(
            "uq_routine_active_user",
            "user_id",
            unique=True,
            postgresql_where=text("is_active = true"),
            sqlite_where=text("is_active = 1"),
        ),
    )


class RoutineDay(Base):
    __tablename__ = "routine_day"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    routine_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("routine.id", ondelete="CASCADE"), index=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer)
    day_type: Mapped[str] = mapped_column(String(10))
    label: Mapped[str | None] = mapped_column(String(80), nullable=True)
    discipline_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("discipline.id", ondelete="SET NULL"), nullable=True
    )
    target_duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    routine: Mapped[Routine] = relationship(back_populates="days")
    exercises: Mapped[list["RoutineExercise"]] = relationship(
        back_populates="routine_day",
        cascade="all, delete-orphan",
        order_by="RoutineExercise.order_index",
    )

    __table_args__ = (
        UniqueConstraint("routine_id", "day_of_week", name="uq_routine_day_weekday"),
        CheckConstraint(
            "day_type IN ('gimnasio', 'deporte', 'descanso')",
            name="ck_routine_day_type",
        ),
        CheckConstraint(
            "day_type = 'deporte' OR discipline_id IS NULL",
            name="ck_routine_day_discipline",
        ),
        CheckConstraint(
            "day_type = 'deporte' OR target_duration_min IS NULL",
            name="ck_routine_day_duration",
        ),
    )


class RoutineExercise(Base):
    __tablename__ = "routine_exercise"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    routine_day_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("routine_day.id", ondelete="CASCADE"), index=True
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("exercise_catalog.id", ondelete="SET NULL")
    )
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    superset_group_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)

    routine_day: Mapped[RoutineDay] = relationship(back_populates="exercises")
    sets: Mapped[list["RoutineSet"]] = relationship(
        back_populates="routine_exercise",
        cascade="all, delete-orphan",
        order_by="RoutineSet.set_number",
    )


class RoutineSet(Base):
    __tablename__ = "routine_set"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    routine_exercise_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("routine_exercise.id", ondelete="CASCADE"), index=True
    )
    set_number: Mapped[int] = mapped_column(Integer)
    set_type: Mapped[str] = mapped_column(String(16), default="normal")
    target_reps_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_reps_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    routine_exercise: Mapped[RoutineExercise] = relationship(back_populates="sets")

    __table_args__ = (
        CheckConstraint(
            "target_reps_min IS NULL OR "
            "(target_reps_min > 0 AND "
            "(target_reps_max IS NULL OR target_reps_max >= target_reps_min))",
            name="ck_routine_set_reps",
        ),
    )
