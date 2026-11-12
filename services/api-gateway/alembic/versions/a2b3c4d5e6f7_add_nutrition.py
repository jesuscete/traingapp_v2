"""add nutrition tables (food, meal_entry, meal_template, body_weight_log, nutrition_goal)

Revision ID: a2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "a2b3c4d5e6f7"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSON = sa.JSON().with_variant(JSONB(), "postgresql")


def _user_fk(nullable: bool = False) -> sa.Column[sa.Uuid]:
    return sa.Column(
        "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=nullable
    )


def upgrade() -> None:
    op.create_table(
        "food",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "owner_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("source", sa.String(10), nullable=False),
        sa.Column("external_id", sa.String(64), nullable=True),
        sa.Column("barcode", sa.String(32), nullable=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("brand", sa.String(120), nullable=True),
        sa.Column("kcal_100g", sa.Float(), nullable=False),
        sa.Column("protein_100g", sa.Float(), nullable=False, server_default="0"),
        sa.Column("carbs_100g", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fat_100g", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fiber_100g", sa.Float(), nullable=True),
        sa.Column("sugar_100g", sa.Float(), nullable=True),
        sa.Column("servings", _JSON, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("source", "external_id", name="uq_food_source_external"),
    )
    op.create_index("ix_food_owner_user_id", "food", ["owner_user_id"])
    op.create_index("ix_food_barcode", "food", ["barcode"])

    op.create_table(
        "meal_entry",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _user_fk(),
        sa.Column("eaten_on", sa.Date(), nullable=False),
        sa.Column("meal", sa.String(10), nullable=False),
        sa.Column(
            "food_id", sa.Uuid(), sa.ForeignKey("food.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("grams", sa.Float(), nullable=True),
        sa.Column("kcal", sa.Float(), nullable=False),
        sa.Column("protein_g", sa.Float(), nullable=False, server_default="0"),
        sa.Column("carbs_g", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fat_g", sa.Float(), nullable=False, server_default="0"),
        sa.Column("fiber_g", sa.Float(), nullable=True),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_meal_entry_user_day", "meal_entry", ["user_id", "eaten_on"])

    op.create_table(
        "meal_template",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _user_fk(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("items", _JSON, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_meal_template_user_id", "meal_template", ["user_id"])

    op.create_table(
        "body_weight_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        _user_fk(),
        sa.Column("measured_on", sa.Date(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=False),
        sa.UniqueConstraint("user_id", "measured_on", name="uq_weight_user_day"),
    )
    op.create_index("ix_body_weight_log_user_id", "body_weight_log", ["user_id"])

    op.create_table(
        "nutrition_goal",
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("goal", sa.String(10), nullable=False, server_default="mantener"),
        sa.Column("target_weight_kg", sa.Float(), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("rate_kg_week", sa.Float(), nullable=True),
        sa.Column("protein_g_per_kg", sa.Float(), nullable=False, server_default="2.0"),
        sa.Column("activity_factor", sa.Float(), nullable=False, server_default="1.4"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("nutrition_goal")
    op.drop_index("ix_body_weight_log_user_id", table_name="body_weight_log")
    op.drop_table("body_weight_log")
    op.drop_index("ix_meal_template_user_id", table_name="meal_template")
    op.drop_table("meal_template")
    op.drop_index("ix_meal_entry_user_day", table_name="meal_entry")
    op.drop_table("meal_entry")
    op.drop_index("ix_food_barcode", table_name="food")
    op.drop_index("ix_food_owner_user_id", table_name="food")
    op.drop_table("food")
