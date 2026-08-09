"""add user_muscle_calibration table

Revision ID: h1b2c3d4e5f6
Revises: g0a1b2c3d4e5
Create Date: 2026-08-08 19:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "h1b2c3d4e5f6"
down_revision: str | None = "g0a1b2c3d4e5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Calibracion personal del modelo de fatiga con DOMS reportado (ADR-015).
    op.create_table(
        "user_muscle_calibration",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("muscle_group", sa.String(length=40), nullable=False),
        sa.Column("ng_delta", sa.Float(), nullable=False, server_default="0"),
        sa.Column("tau2_factor", sa.Float(), nullable=False, server_default="1"),
        sa.Column("sample_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pearson_r", sa.Float(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id", "muscle_group", name="uq_user_calibration_muscle_group"
        ),
    )


def downgrade() -> None:
    op.drop_table("user_muscle_calibration")
