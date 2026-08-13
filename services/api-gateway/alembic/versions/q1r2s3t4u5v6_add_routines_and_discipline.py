"""add routines and discipline catalog

Revision ID: q1r2s3t4u5v6
Revises: j2k3l4m5n6o7
Create Date: 2026-08-09 15:00:00.000000

Introduce la rutina como plantilla recurrente (plan semanal sin pesos):
routine -> routine_day -> routine_exercise -> routine_set. Se crea ademas el
catalogo `discipline` (sustituye al enum de disciplinas) y se anade
`training_sessions.routine_day_id` (nullable) para poder vincular en el
futuro una sesion real con el dia de rutina que la origino.
"""
import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "q1r2s3t4u5v6"
down_revision: str | None = "j2k3l4m5n6o7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DISCIPLINES: tuple[tuple[str, str, float], ...] = (
    ("Gimnasio", "gimnasio", 5.0),
    ("Boxeo", "boxeo", 7.8),
    ("Running", "running", 8.2),
    ("Ciclismo", "ciclismo", 7.1),
    ("Natación", "natacion", 6.0),
    ("Otro", "otro", 4.0),
)


def upgrade() -> None:
    op.create_table(
        "discipline",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("normalized_name", sa.String(length=80), nullable=False),
        sa.Column("met", sa.Float(), nullable=False, server_default="4.0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_discipline_normalized_name"), "discipline", ["normalized_name"]
    )
    for name, normalized, met in _DISCIPLINES:
        op.execute(
            sa.text(
                "INSERT INTO discipline (id, name, normalized_name, met) "
                "VALUES (:id, :name, :normalized, :met)"
            ).bindparams(
                id=uuid.uuid4(),
                name=name,
                normalized=normalized,
                met=met,
            )
        )

    op.create_table(
        "routine",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_routine_user_id"), "routine", ["user_id"])
    op.create_index(
        "uq_routine_active_user",
        "routine",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
        sqlite_where=sa.text("is_active = 1"),
    )

    op.create_table(
        "routine_day",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "routine_id",
            sa.Uuid(),
            sa.ForeignKey("routine.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("day_of_week", sa.Integer(), nullable=False),
        sa.Column("day_type", sa.String(length=10), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=True),
        sa.Column(
            "discipline_id",
            sa.Uuid(),
            sa.ForeignKey("discipline.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("target_duration_min", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("routine_id", "day_of_week", name="uq_routine_day_weekday"),
        sa.CheckConstraint(
            "day_type IN ('gimnasio', 'deporte', 'descanso')",
            name="ck_routine_day_type",
        ),
        sa.CheckConstraint(
            "day_type = 'deporte' OR discipline_id IS NULL",
            name="ck_routine_day_discipline",
        ),
        sa.CheckConstraint(
            "day_type = 'deporte' OR target_duration_min IS NULL",
            name="ck_routine_day_duration",
        ),
    )
    op.create_index(
        op.f("ix_routine_day_routine_id"), "routine_day", ["routine_id"]
    )

    op.create_table(
        "routine_exercise",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "routine_day_id",
            sa.Uuid(),
            sa.ForeignKey("routine_day.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exercise_id",
            sa.Uuid(),
            sa.ForeignKey("exercise_catalog.id", ondelete="SET NULL"),
            nullable=False,
        ),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("superset_group_id", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_routine_exercise_routine_day_id"),
        "routine_exercise",
        ["routine_day_id"],
    )

    op.create_table(
        "routine_set",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "routine_exercise_id",
            sa.Uuid(),
            sa.ForeignKey("routine_exercise.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("set_number", sa.Integer(), nullable=False),
        sa.Column("set_type", sa.String(length=16), nullable=False, server_default="normal"),
        sa.Column("target_reps_min", sa.Integer(), nullable=False),
        sa.Column("target_reps_max", sa.Integer(), nullable=True),
        sa.Column("target_rest_seconds", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint(
            "target_reps_min > 0 AND "
            "(target_reps_max IS NULL OR target_reps_max >= target_reps_min)",
            name="ck_routine_set_reps",
        ),
    )
    op.create_index(
        op.f("ix_routine_set_routine_exercise_id"),
        "routine_set",
        ["routine_exercise_id"],
    )

    op.add_column(
        "training_sessions",
        sa.Column(
            "routine_day_id",
            sa.Uuid(),
            sa.ForeignKey("routine_day.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_training_sessions_routine_day_id"),
        "training_sessions",
        ["routine_day_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_training_sessions_routine_day_id"), table_name="training_sessions"
    )
    op.drop_column("training_sessions", "routine_day_id")
    op.drop_index(op.f("ix_routine_set_routine_exercise_id"), table_name="routine_set")
    op.drop_table("routine_set")
    op.drop_index(
        op.f("ix_routine_exercise_routine_day_id"), table_name="routine_exercise"
    )
    op.drop_table("routine_exercise")
    op.drop_index(op.f("ix_routine_day_routine_id"), table_name="routine_day")
    op.drop_table("routine_day")
    op.drop_index("uq_routine_active_user", table_name="routine")
    op.drop_index(op.f("ix_routine_user_id"), table_name="routine")
    op.drop_table("routine")
    op.drop_index(op.f("ix_discipline_normalized_name"), table_name="discipline")
    op.drop_table("discipline")
