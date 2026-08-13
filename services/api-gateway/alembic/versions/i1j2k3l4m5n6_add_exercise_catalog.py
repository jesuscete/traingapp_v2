"""add exercise_catalog table (canonical exercise catalog, seed)

Revision ID: i1j2k3l4m5n6
Revises: h1b2c3d4e5f6
Create Date: 2026-08-09 10:00:00.000000

"""
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op
from app.analytics.exercise_seed import EXERCISE_CATALOG_SEED

revision: str = "i1j2k3l4m5n6"
down_revision: str | None = "h1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exercise_catalog",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("normalized_name", sa.String(length=120), nullable=False),
        sa.Column("exercise_type", sa.String(length=20), nullable=False),
        sa.Column("muscles", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "normalized_name", name="uq_exercise_catalog_normalized_name"
        ),
    )

    catalog_table = sa.table(
        "exercise_catalog",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("normalized_name", sa.String()),
        sa.column("exercise_type", sa.String()),
        sa.column("muscles", JSONB()),
    )
    op.bulk_insert(
        catalog_table,
        [
            {
                "id": uuid.uuid4(),
                "name": entry["name"],
                "normalized_name": entry["normalized_name"],
                "exercise_type": entry["exercise_type"],
                "muscles": entry["muscles"],
            }
            for entry in EXERCISE_CATALOG_SEED
        ],
    )


def downgrade() -> None:
    op.drop_table("exercise_catalog")
