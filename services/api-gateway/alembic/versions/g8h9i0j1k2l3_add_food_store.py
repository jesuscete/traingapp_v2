"""food.store: supermercado de origen (importaciones de Open Food Facts por tienda)

Revision ID: g8h9i0j1k2l3
Revises: f7a8b9c0d1e2
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "g8h9i0j1k2l3"
down_revision: str | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("food", sa.Column("store", sa.String(40), nullable=True))
    op.create_index("ix_food_store", "food", ["store"])


def downgrade() -> None:
    op.drop_index("ix_food_store", table_name="food")
    op.drop_column("food", "store")
