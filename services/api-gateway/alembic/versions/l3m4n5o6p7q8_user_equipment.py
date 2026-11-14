"""users.equipment: material con el que entrena el usuario (M10 · base de conocimiento)

Revision ID: l3m4n5o6p7q8
Revises: k2l3m4n5o6p7
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "l3m4n5o6p7q8"
down_revision: str | None = "k2l3m4n5o6p7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "equipment",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "equipment")
