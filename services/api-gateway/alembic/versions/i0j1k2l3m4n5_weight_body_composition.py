"""peso: % de grasa y % de músculo opcionales (básculas de bioimpedancia)

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "i0j1k2l3m4n5"
down_revision: str | None = "h9i0j1k2l3m4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("body_weight_log", sa.Column("body_fat_pct", sa.Float(), nullable=True))
    op.add_column("body_weight_log", sa.Column("muscle_pct", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("body_weight_log", "muscle_pct")
    op.drop_column("body_weight_log", "body_fat_pct")
