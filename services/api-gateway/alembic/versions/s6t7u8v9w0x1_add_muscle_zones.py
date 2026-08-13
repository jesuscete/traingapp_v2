"""add zone_code to muscle and seed fine core muscles

Revision ID: s6t7u8v9w0x1
Revises: r5s6t7u8v9w0
Create Date: 2026-08-10
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.analytics.catalog_seed import MUSCLE_SEED, MUSCLE_ZONE_OF

revision: str = "s6t7u8v9w0x1"
down_revision: str | None = "r5s6t7u8v9w0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _muscle_table() -> sa.Table:
    return sa.table(
        "muscle",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("label", sa.String()),
        sa.column("rollup_code", sa.String()),
        sa.column("zone_code", sa.String()),
    )


def _seed_and_backfill_zones() -> None:
    """Inserta los musculos finos de core que falten y rellena zone_code."""
    bind = op.get_bind()
    existing = {
        row[0]
        for row in bind.execute(sa.text("SELECT code FROM muscle")).fetchall()
    }
    rows = [
        {
            "id": uuid.uuid4(),
            "code": code,
            "label": label,
            "rollup_code": rollup,
            "zone_code": MUSCLE_ZONE_OF[code],
        }
        for code, label, rollup in MUSCLE_SEED
        if code not in existing
    ]
    if rows:
        op.bulk_insert(_muscle_table(), rows)
    for code, _, _ in MUSCLE_SEED:
        bind.execute(
            sa.text("UPDATE muscle SET zone_code = :zone WHERE code = :code"),
            {"zone": MUSCLE_ZONE_OF[code], "code": code},
        )


def upgrade() -> None:
    op.add_column(
        "muscle",
        sa.Column("zone_code", sa.String(40), nullable=True, index=True),
    )
    _seed_and_backfill_zones()
    op.alter_column(
        "muscle",
        "zone_code",
        existing_type=sa.String(40),
        nullable=False,
    )


def downgrade() -> None:
    bind = op.get_bind()
    for code in ("upper_abs", "lower_abs", "obliques"):
        bind.execute(
            sa.text("DELETE FROM muscle WHERE code = :code"), {"code": code}
        )
    op.drop_index("ix_muscle_zone_code", table_name="muscle")
    op.drop_column("muscle", "zone_code")
