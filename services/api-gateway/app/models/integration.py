import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

_JSONB = JSON().with_variant(JSONB(), "postgresql")


class GarminConnection(Base):
    """Conexión con la API personal de Garmin. La clave y el token se guardan cifrados."""

    __tablename__ = "garmin_connections"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    api_key_enc: Mapped[str] = mapped_column(Text)
    token_enc: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="ok")  # ok | error | syncing
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_result: Mapped[dict[str, object] | None] = mapped_column(_JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
