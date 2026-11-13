"""Nutrición (M5): alimentos, comidas, platos guardados, peso corporal y objetivos."""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

_JSONB = JSON().with_variant(JSONB(), "postgresql")


class Food(Base):
    """Alimento con valores por 100 g. Caché de fuentes externas o alimento propio."""

    __tablename__ = "food"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_food_source_external"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    # NULL = compartido (caché de OFF/USDA); si no, alimento propio de ese usuario.
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    source: Mapped[str] = mapped_column(String(10))  # off | usda | custom | ia
    external_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    barcode: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Supermercado de origen (p. ej. "Lidl") cuando viene de una importacion por tienda.
    store: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    kcal_100g: Mapped[float] = mapped_column(Float)
    protein_100g: Mapped[float] = mapped_column(Float, default=0)
    carbs_100g: Mapped[float] = mapped_column(Float, default=0)
    fat_100g: Mapped[float] = mapped_column(Float, default=0)
    fiber_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    sugar_100g: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Raciones típicas: [{"label": "1 huevo", "grams": 50}]
    servings: Mapped[list[dict[str, object]]] = mapped_column(_JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MealEntry(Base):
    """Una línea de comida. Copia los macros para que el historial no cambie."""

    __tablename__ = "meal_entry"
    __table_args__ = (Index("ix_meal_entry_user_day", "user_id", "eaten_on"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE")
    )
    eaten_on: Mapped[date] = mapped_column(Date)
    # desayuno|media_manana|comida|merienda|cena|dia
    meal: Mapped[str] = mapped_column(String(16))
    food_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("food.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200))
    grams: Mapped[float | None] = mapped_column(Float, nullable=True)
    kcal: Mapped[float] = mapped_column(Float)
    protein_g: Mapped[float] = mapped_column(Float, default=0)
    carbs_g: Mapped[float] = mapped_column(Float, default=0)
    fat_g: Mapped[float] = mapped_column(Float, default=0)
    fiber_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    # pesada | etiqueta (exactas) · racion | rapida | ia (estimadas)
    method: Mapped[str] = mapped_column(String(10))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class MealTemplate(Base):
    """'Mis platos': lista de alimentos y gramos que se añade de un toque."""

    __tablename__ = "meal_template"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(120))
    # [{"food_id": "...", "grams": 120}]
    items: Mapped[list[dict[str, object]]] = mapped_column(_JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class BodyWeightLog(Base):
    __tablename__ = "body_weight_log"
    __table_args__ = (UniqueConstraint("user_id", "measured_on", name="uq_weight_user_day"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    measured_on: Mapped[date] = mapped_column(Date)
    weight_kg: Mapped[float] = mapped_column(Float)
    body_fat_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    muscle_pct: Mapped[float | None] = mapped_column(Float, nullable=True)


class NutritionGoal(Base):
    __tablename__ = "nutrition_goal"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    goal: Mapped[str] = mapped_column(String(10), default="mantener")  # perder|mantener|ganar|corte
    target_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    rate_kg_week: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein_g_per_kg: Mapped[float] = mapped_column(Float, default=2.0)
    # Actividad cotidiana SIN entrenos (los entrenos se suman aparte con sus kcal reales).
    activity_factor: Mapped[float] = mapped_column(Float, default=1.4)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
