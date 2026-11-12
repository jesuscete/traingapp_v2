"""activity import: HR profile, external ids on sessions, activity_stream

Revision ID: b3c4d5e6f7a8
Revises: a2b3c4d5e6f7
Create Date: 2026-11-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "b3c4d5e6f7a8"
down_revision: str | None = "a2b3c4d5e6f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_JSON = sa.JSON().with_variant(JSONB(), "postgresql")


def upgrade() -> None:
    op.add_column("users", sa.Column("max_hr", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("resting_hr", sa.Integer(), nullable=True))
    op.add_column("training_sessions", sa.Column("external_source", sa.String(20), nullable=True))
    op.add_column("training_sessions", sa.Column("external_id", sa.String(80), nullable=True))
    op.create_unique_constraint(
        "uq_training_sessions_external",
        "training_sessions",
        ["user_id", "external_source", "external_id"],
    )
    op.create_table(
        "activity_stream",
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("training_sessions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("samples", _JSON, nullable=False),
        sa.Column("laps", _JSON, nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_table("activity_stream")
    op.drop_constraint("uq_training_sessions_external", "training_sessions", type_="unique")
    op.drop_column("training_sessions", "external_id")
    op.drop_column("training_sessions", "external_source")
    op.drop_column("users", "resting_hr")
    op.drop_column("users", "max_hr")
