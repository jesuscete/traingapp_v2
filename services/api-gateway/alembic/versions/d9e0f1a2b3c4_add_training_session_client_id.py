"""add client_id to training_sessions (idempotent retries)

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-11-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d9e0f1a2b3c4"
down_revision: str | None = "c8d9e0f1a2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("training_sessions", sa.Column("client_id", sa.Uuid(), nullable=True))
    op.create_unique_constraint(
        "uq_training_sessions_user_client", "training_sessions", ["user_id", "client_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_training_sessions_user_client", "training_sessions", type_="unique")
    op.drop_column("training_sessions", "client_id")
