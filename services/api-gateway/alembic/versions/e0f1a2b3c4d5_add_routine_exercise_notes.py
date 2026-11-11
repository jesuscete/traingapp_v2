"""add notes to routine_exercise

Revision ID: e0f1a2b3c4d5
Revises: d9e0f1a2b3c4
Create Date: 2026-11-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e0f1a2b3c4d5"
down_revision: str | None = "d9e0f1a2b3c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("routine_exercise", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("routine_exercise", "notes")
