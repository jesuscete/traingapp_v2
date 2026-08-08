"""add optional cardio and workout type fields

Revision ID: a1b2c3d4e5f6
Revises: 4acbeef1713b
Create Date: 2026-08-08 12:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "4acbeef1713b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "training_sessions", sa.Column("workout_type", sa.String(length=40), nullable=True)
    )
    op.add_column("training_sessions", sa.Column("distance_meters", sa.Float(), nullable=True))
    op.add_column("training_sessions", sa.Column("avg_heart_rate", sa.Float(), nullable=True))
    op.add_column("training_sessions", sa.Column("max_heart_rate", sa.Float(), nullable=True))
    op.add_column("training_sessions", sa.Column("elevation_gain_m", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("training_sessions", "elevation_gain_m")
    op.drop_column("training_sessions", "max_heart_rate")
    op.drop_column("training_sessions", "avg_heart_rate")
    op.drop_column("training_sessions", "distance_meters")
    op.drop_column("training_sessions", "workout_type")
