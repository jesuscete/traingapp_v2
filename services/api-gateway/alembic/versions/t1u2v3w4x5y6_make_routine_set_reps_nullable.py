"""make routine_set.target_reps_min nullable

Revision ID: t1u2v3w4x5y6
Revises: s6t7u8v9w0x1
Create Date: 2026-08-10

Permite que una serie objetivo de rutina se guarde sin repeticiones
(`target_reps_min = NULL`): las repes son opcionales al configurar el dia
de gimnasio desde el editor. Se relaja el check `ck_routine_set_reps` para
que admita NULL.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "t1u2v3w4x5y6"
down_revision: str | None = "s6t7u8v9w0x1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_NEW_REPS_CHECK = (
    "target_reps_min IS NULL OR "
    "(target_reps_min > 0 AND "
    "(target_reps_max IS NULL OR target_reps_max >= target_reps_min))"
)


def upgrade() -> None:
    with op.batch_alter_table("routine_set") as batch_op:
        batch_op.drop_constraint("ck_routine_set_reps", type_="check")
        batch_op.alter_column(
            "target_reps_min", existing_type=sa.Integer(), nullable=True
        )
        batch_op.create_check_constraint("ck_routine_set_reps", _NEW_REPS_CHECK)


def downgrade() -> None:
    with op.batch_alter_table("routine_set") as batch_op:
        batch_op.drop_constraint("ck_routine_set_reps", type_="check")
        batch_op.create_check_constraint(
            "ck_routine_set_reps",
            "target_reps_min > 0 AND "
            "(target_reps_max IS NULL OR target_reps_max >= target_reps_min)",
        )
        batch_op.alter_column(
            "target_reps_min", existing_type=sa.Integer(), nullable=False
        )
