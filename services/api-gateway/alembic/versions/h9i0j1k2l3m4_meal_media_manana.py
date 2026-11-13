"""comidas: 5 tomas (desayuno, media mañana, comida, merienda, cena); snack -> media_manana

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2026-11-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "h9i0j1k2l3m4"
down_revision: str | None = "g8h9i0j1k2l3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "meal_entry", "meal", type_=sa.String(16), existing_type=sa.String(10), nullable=False
    )
    op.execute("UPDATE meal_entry SET meal = 'media_manana' WHERE meal = 'snack'")


def downgrade() -> None:
    op.execute("UPDATE meal_entry SET meal = 'snack' WHERE meal = 'media_manana'")
    op.alter_column(
        "meal_entry", "meal", type_=sa.String(10), existing_type=sa.String(16), nullable=False
    )
