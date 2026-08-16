"""Perfiles de entrenamiento y su prompt asociado (modelo de IA por disciplina).

El catalogo de disciplinas agrupa deportes con demandas fisicas similares en
perfiles de entrenamiento (`training_prompt`). Cada perfil define una plantilla
de prompt con placeholders (`{deportes}`, `{dias_gimnasio}`, `{objetivo}`, ...)
que la IA usara al recomendar una rutina. La relacion
`discipline_training_prompt` asigna una disciplina a su perfil (N disciplinas
pueden compartir un mismo perfil); si una disciplina no tiene perfil asignado,
el sistema cae en el prompt por defecto (`is_default = true`, rutina
equilibrada).
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.routine import Discipline


class TrainingPrompt(Base):
    """Perfil de entrenamiento con su plantilla de prompt para la IA."""

    __tablename__ = "training_prompt"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default="")
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    disciplines: Mapped[list["DisciplineTrainingPrompt"]] = relationship(
        back_populates="training_prompt",
        cascade="all, delete-orphan",
    )


class DisciplineTrainingPrompt(Base):
    """Asignacion disciplina -> perfil de entrenamiento.

    Una disciplina puede tener como mucho un perfil (`unique` sobre
    `discipline_id`), pero varios deportes comparten el mismo `training_prompt`.
    """

    __tablename__ = "discipline_training_prompt"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    discipline_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("discipline.id", ondelete="CASCADE"), index=True
    )
    training_prompt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("training_prompt.id", ondelete="CASCADE"), index=True
    )

    discipline: Mapped["Discipline"] = relationship()
    training_prompt: Mapped[TrainingPrompt] = relationship(back_populates="disciplines")

    __table_args__ = (
        UniqueConstraint("discipline_id", name="uq_discipline_training_prompt_discipline"),
    )
