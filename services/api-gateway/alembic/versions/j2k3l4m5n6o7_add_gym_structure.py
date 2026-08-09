"""add gym structure (workout_exercise, set, set_entry, summary) + catalog flags

Revision ID: j2k3l4m5n6o7
Revises: i1j2k3l4m5n6
Create Date: 2026-08-09 14:00:00.000000

Modelo de 4 niveles para gimnasio: training_sessions (workout_session) ->
workout_exercise -> set -> set_entry. `workout_session_summary` es el resumen
materializado. El catalogo `exercise_catalog` gana uses_bodyweight/unilateral
y el mapa muscular se renombra a muscle_map (misma columna JSONB).
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "j2k3l4m5n6o7"
down_revision: str | None = "i1j2k3l4m5n6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BODYWEIGHT = ("dominadas", "fondos en paralelas", "plancha")
_UNILATERAL = ("zancadas", "remo mancuerna")


def upgrade() -> None:
    # --- Catalogo: rename muscles -> muscle_map + flags ---
    op.alter_column("exercise_catalog", "muscles", new_column_name="muscle_map")
    op.add_column(
        "exercise_catalog",
        sa.Column(
            "uses_bodyweight", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.add_column(
        "exercise_catalog",
        sa.Column(
            "unilateral", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    for name in _BODYWEIGHT:
        op.execute(
            sa.text(
                "UPDATE exercise_catalog SET uses_bodyweight = true "
                "WHERE normalized_name = :name"
            ).bindparams(name=name)
        )
    for name in _UNILATERAL:
        op.execute(
            sa.text(
                "UPDATE exercise_catalog SET unilateral = true "
                "WHERE normalized_name = :name"
            ).bindparams(name=name)
        )

    # --- training_sessions (= workout_session) ---
    op.add_column(
        "training_sessions",
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "training_sessions",
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "training_sessions", sa.Column("intensity", sa.Integer(), nullable=True)
    )
    op.add_column("training_sessions", sa.Column("fatigue", sa.Integer(), nullable=True))

    # --- workout_exercise ---
    op.create_table(
        "workout_exercise",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("training_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "exercise_id",
            sa.Uuid(),
            sa.ForeignKey("exercise_catalog.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("superset_group_id", sa.Uuid(), nullable=True),
        sa.Column("volume_kg", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_workout_exercise_session_id"), "workout_exercise", ["session_id"]
    )
    op.create_index(
        op.f("ix_workout_exercise_exercise_id"), "workout_exercise", ["exercise_id"]
    )

    # --- set ---
    op.create_table(
        "set",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "workout_exercise_id",
            sa.Uuid(),
            sa.ForeignKey("workout_exercise.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("set_number", sa.Integer(), nullable=False),
        sa.Column("set_type", sa.String(length=16), nullable=False, server_default="normal"),
        sa.Column("rest_seconds", sa.Integer(), nullable=True),
        sa.Column("is_warmup", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("volume_kg", sa.Float(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_set_workout_exercise_id"), "set", ["workout_exercise_id"]
    )

    # --- set_entry ---
    op.create_table(
        "set_entry",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "set_id",
            sa.Uuid(),
            sa.ForeignKey("set.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entry_order", sa.Integer(), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("weight_unit", sa.String(length=3), nullable=False, server_default="kg"),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("distance_meters", sa.Float(), nullable=True),
        sa.Column("rpe", sa.Integer(), nullable=True),
        sa.Column("side", sa.String(length=8), nullable=False, server_default="both"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_set_entry_set_id"), "set_entry", ["set_id"])

    # --- workout_session_summary ---
    op.create_table(
        "workout_session_summary",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "session_id",
            sa.Uuid(),
            sa.ForeignKey("training_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("total_volume", sa.Float(), nullable=False, server_default="0"),
        sa.Column("avg_rpe", sa.Float(), nullable=True),
        sa.Column("sets_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_min", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", name="uq_workout_session_summary_session"),
    )
    op.create_index(
        op.f("ix_workout_session_summary_session_id"),
        "workout_session_summary",
        ["session_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_workout_session_summary_session_id"), table_name="workout_session_summary"
    )
    op.drop_table("workout_session_summary")
    op.drop_index(op.f("ix_set_entry_set_id"), table_name="set_entry")
    op.drop_table("set_entry")
    op.drop_index(op.f("ix_set_workout_exercise_id"), table_name="set")
    op.drop_table("set")
    op.drop_index(op.f("ix_workout_exercise_exercise_id"), table_name="workout_exercise")
    op.drop_index(op.f("ix_workout_exercise_session_id"), table_name="workout_exercise")
    op.drop_table("workout_exercise")
    op.drop_column("training_sessions", "fatigue")
    op.drop_column("training_sessions", "intensity")
    op.drop_column("training_sessions", "end_time")
    op.drop_column("training_sessions", "start_time")
    for name in _UNILATERAL:
        op.execute(
            sa.text(
                "UPDATE exercise_catalog SET unilateral = false "
                "WHERE normalized_name = :name"
            ).bindparams(name=name)
        )
    for name in _BODYWEIGHT:
        op.execute(
            sa.text(
                "UPDATE exercise_catalog SET uses_bodyweight = false "
                "WHERE normalized_name = :name"
            ).bindparams(name=name)
        )
    op.drop_column("exercise_catalog", "unilateral")
    op.drop_column("exercise_catalog", "uses_bodyweight")
    op.alter_column("exercise_catalog", "muscle_map", new_column_name="muscles")
