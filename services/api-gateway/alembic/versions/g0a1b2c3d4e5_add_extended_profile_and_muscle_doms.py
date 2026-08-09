"""add extended profile fields, readiness hrv/rhr and muscle doms table

Revision ID: g0a1b2c3d4e5
Revises: f6a7b8c9d0e1
Create Date: 2026-08-08 18:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "g0a1b2c3d4e5"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Perfil de usuario ampliado (ADR-010/011/013 y P1).
    op.add_column("users", sa.Column("body_fat_pct", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("fitness_level", sa.String(length=20), nullable=True))
    op.add_column("users", sa.Column("weekly_availability", sa.Integer(), nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "injuries",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "goals",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )

    # Readiness: HRV y frecuencia cardíaca en reposo para proyección futura.
    op.add_column("daily_readiness", sa.Column("hrv_score", sa.Float(), nullable=True))
    op.add_column("daily_readiness", sa.Column("resting_hr", sa.Float(), nullable=True))

    # DOMS localizado por grupo muscular (mapa corporal, ADR-011).
    op.create_table(
        "daily_muscle_doms",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("muscle_group", sa.String(length=40), nullable=False),
        sa.Column("pain", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "date", "muscle_group", name="uq_user_date_muscle_group"),
    )


def downgrade() -> None:
    op.drop_table("daily_muscle_doms")
    op.drop_column("daily_readiness", "resting_hr")
    op.drop_column("daily_readiness", "hrv_score")
    op.drop_column("users", "goals")
    op.drop_column("users", "injuries")
    op.drop_column("users", "weekly_availability")
    op.drop_column("users", "fitness_level")
    op.drop_column("users", "body_fat_pct")
