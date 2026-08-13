import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

_JSONB = JSON().with_variant(JSONB(), "postgresql")


class ExerciseCatalog(Base):
    """Catalogo canonico de ejercicios.

    `muscle_map` es una cache desnormalizada (rollup por grupo) que mantienen
    los seeds en sincronia con la tabla relacional `exercise_muscle` (fuente de
    verdad de la relacion ejercicio <-> musculo con su peso de activacion).
    """

    __tablename__ = "exercise_catalog"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    normalized_name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    exercise_type: Mapped[str] = mapped_column(String(20))
    muscle_map: Mapped[dict[str, float]] = mapped_column(_JSONB)
    uses_bodyweight: Mapped[bool] = mapped_column(Boolean, default=False)
    unilateral: Mapped[bool] = mapped_column(Boolean, default=False)
    images: Mapped[list[str]] = mapped_column(_JSONB, default=list)
    details: Mapped[dict[str, object]] = mapped_column(_JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    muscles: Mapped[list["ExerciseMuscle"]] = relationship(
        back_populates="exercise", cascade="all, delete-orphan"
    )


class Muscle(Base):
    """Grupo muscular canonico.

    `code` es la clave interna (ej. "quadriceps"); `rollup_code` agrupa el
    musculo en uno de los 12 grupos de fatiga (ej. "lats" -> "back") para que
    la analitica de fatiga/volumen siga trabajando sobre el mismo conjunto;
    `zone_code` lo agrupa en una de las 7 zonas de los graficos de radar
    (ej. "abdominals" -> "core", "lats" -> "back").
    """

    __tablename__ = "muscle"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    label: Mapped[str] = mapped_column(String(80))
    rollup_code: Mapped[str] = mapped_column(String(40), index=True)
    zone_code: Mapped[str] = mapped_column(String(40), default="other", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    exercises: Mapped[list["ExerciseMuscle"]] = relationship(
        back_populates="muscle", cascade="all, delete-orphan"
    )


class ExerciseMuscle(Base):
    """Relacion ejercicio <-> musculo con peso de activacion (0-1).

    `activation` representa la carga relativa que el ejercicio impone sobre el
    musculo (los primarios pesan mas que los secundarios; la suma por ejercicio
    es <= 1). `is_primary` marca si el musculo es objetivo principal.
    """

    __tablename__ = "exercise_muscle"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("exercise_catalog.id", ondelete="CASCADE"), index=True
    )
    muscle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("muscle.id", ondelete="CASCADE"), index=True
    )
    activation: Mapped[float] = mapped_column(Float, default=0.0)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    exercise: Mapped[ExerciseCatalog] = relationship(back_populates="muscles")
    muscle: Mapped[Muscle] = relationship(back_populates="exercises")
