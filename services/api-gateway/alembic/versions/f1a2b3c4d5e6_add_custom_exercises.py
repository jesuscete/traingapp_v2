"""custom exercises: owner_user_id on exercise_catalog

Revision ID: f1a2b3c4d5e6
Revises: e0f1a2b3c4d5
Create Date: 2026-11-12

El nombre normalizado pasa a ser único por propietario: global (owner NULL) con
un índice parcial, y por usuario con una restricción (owner_user_id, normalized_name).
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e0f1a2b3c4d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "exercise_catalog",
        sa.Column(
            "owner_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_exercise_catalog_owner_user_id", "exercise_catalog", ["owner_user_id"])
    op.drop_constraint("uq_exercise_catalog_normalized_name", "exercise_catalog", type_="unique")
    op.create_index("ix_exercise_catalog_normalized_name", "exercise_catalog", ["normalized_name"])
    op.create_unique_constraint(
        "uq_exercise_owner_name", "exercise_catalog", ["owner_user_id", "normalized_name"]
    )
    op.create_index(
        "uq_exercise_catalog_global_name",
        "exercise_catalog",
        ["normalized_name"],
        unique=True,
        postgresql_where=sa.text("owner_user_id IS NULL"),
        sqlite_where=sa.text("owner_user_id IS NULL"),
    )


def downgrade() -> None:
    op.execute("DELETE FROM exercise_catalog WHERE owner_user_id IS NOT NULL")
    op.drop_index("uq_exercise_catalog_global_name", table_name="exercise_catalog")
    op.drop_constraint("uq_exercise_owner_name", "exercise_catalog", type_="unique")
    op.drop_index("ix_exercise_catalog_normalized_name", table_name="exercise_catalog")
    op.create_unique_constraint(
        "uq_exercise_catalog_normalized_name", "exercise_catalog", ["normalized_name"]
    )
    op.drop_index("ix_exercise_catalog_owner_user_id", table_name="exercise_catalog")
    op.drop_column("exercise_catalog", "owner_user_id")
