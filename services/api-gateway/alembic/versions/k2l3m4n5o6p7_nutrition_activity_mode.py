"""nutrition_goal.activity_mode: gasto por entrenos registrados o factor estimado

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "k2l3m4n5o6p7"
down_revision: str | None = "j1k2l3m4n5o6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "nutrition_goal",
        sa.Column("activity_mode", sa.String(10), nullable=False, server_default="registro"),
    )


def downgrade() -> None:
    op.drop_column("nutrition_goal", "activity_mode")
