"""add user profile fields

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-08 12:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("weight_kg", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("height_cm", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("birth_year", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("goal", sa.String(length=40), nullable=True))
    op.add_column("users", sa.Column("sports", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "sports")
    op.drop_column("users", "goal")
    op.drop_column("users", "birth_year")
    op.drop_column("users", "height_cm")
    op.drop_column("users", "weight_kg")
