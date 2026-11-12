"""Series temporales de actividades importadas (M6): FC, ritmo, altitud, cadencia, potencia."""

import uuid

from sqlalchemy import JSON, ForeignKey, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

_JSONB = JSON().with_variant(JSONB(), "postgresql")


class ActivityStream(Base):
    """Una fila por sesión. `samples` = arrays alineados ({"t": [...], "hr": [...], ...})."""

    __tablename__ = "activity_stream"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("training_sessions.id", ondelete="CASCADE"), primary_key=True
    )
    samples: Mapped[dict[str, list[float | None]]] = mapped_column(_JSONB)
    laps: Mapped[list[dict[str, object]]] = mapped_column(_JSONB, default=list)
