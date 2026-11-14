"""food_alias: diccionario de comidas que aprende (M10 · comidas con IA mínima)

Revision ID: m4n5o6p7q8r9
Revises: l3m4n5o6p7q8
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "m4n5o6p7q8r9"
down_revision: str | None = "l3m4n5o6p7q8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "food_alias",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("alias", sa.String(200), nullable=False),
        sa.Column(
            "owner_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "items",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.Column("source", sa.String(10), nullable=False, server_default="ia"),
        sa.Column("uses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("owner_user_id", "alias", name="uq_food_alias_owner_alias"),
    )
    op.create_index("ix_food_alias_alias", "food_alias", ["alias"])
    op.create_index("ix_food_alias_owner_user_id", "food_alias", ["owner_user_id"])
    op.create_index(
        "uq_food_alias_global",
        "food_alias",
        ["alias"],
        unique=True,
        postgresql_where=sa.text("owner_user_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_food_alias_global", table_name="food_alias")
    op.drop_index("ix_food_alias_owner_user_id", table_name="food_alias")
    op.drop_index("ix_food_alias_alias", table_name="food_alias")
    op.drop_table("food_alias")
