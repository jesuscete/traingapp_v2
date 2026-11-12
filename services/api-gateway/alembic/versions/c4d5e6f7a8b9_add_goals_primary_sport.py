"""goals and primary sport

Revision ID: c4d5e6f7a8b9
Revises: b3c4d5e6f7a8
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c4d5e6f7a8b9"
down_revision: str | None = "b3c4d5e6f7a8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("primary_sport", sa.String(40), nullable=True))
    op.create_table(
        "user_goals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("sport", sa.String(40), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("target_value", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("done", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_user_goals_user_id", "user_goals", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_goals_user_id", table_name="user_goals")
    op.drop_table("user_goals")
    op.drop_column("users", "primary_sport")
