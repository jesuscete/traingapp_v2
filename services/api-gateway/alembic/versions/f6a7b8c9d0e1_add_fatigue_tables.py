"""add fatigue tables and seed muscle load catalog

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-08 16:00:00.000000

"""
import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MUSCLE_GROUPS = [
    "quadriceps", "hamstrings", "glutes", "calves", "core", "back",
    "chest", "shoulders", "biceps", "triceps", "forearms", "neck",
]

# Semilla del catalogo. Fuente canonica documentada en docs/architecture/fatigue-spec.md.
MUSCLE_LOAD_DEFAULT: dict[str, dict[str, float]] = {
    "boxing": {
        "shoulders": 0.95, "triceps": 0.85, "forearms": 0.80, "core": 0.90,
        "neck": 0.70, "biceps": 0.55, "quadriceps": 0.55, "back": 0.50,
        "glutes": 0.45, "hamstrings": 0.45, "calves": 0.45, "chest": 0.40,
    },
    "running": {
        "calves": 0.95, "quadriceps": 0.85, "hamstrings": 0.85, "glutes": 0.70,
        "core": 0.45, "back": 0.30, "neck": 0.20, "shoulders": 0.20,
        "chest": 0.10, "biceps": 0.10, "triceps": 0.10, "forearms": 0.10,
    },
    "gym": {
        "chest": 0.80, "back": 0.75, "shoulders": 0.70, "biceps": 0.65,
        "triceps": 0.65, "quadriceps": 0.65, "core": 0.55, "glutes": 0.50,
        "forearms": 0.45, "hamstrings": 0.45, "calves": 0.35, "neck": 0.30,
    },
    "calisthenics": {
        "core": 0.90, "back": 0.85, "shoulders": 0.85, "biceps": 0.85,
        "triceps": 0.85, "chest": 0.80, "forearms": 0.75, "quadriceps": 0.55,
        "calves": 0.45, "glutes": 0.40, "neck": 0.30, "hamstrings": 0.30,
    },
    "football": {
        "quadriceps": 0.90, "hamstrings": 0.90, "glutes": 0.80, "calves": 0.90,
        "core": 0.50, "back": 0.30, "chest": 0.20, "shoulders": 0.30,
        "biceps": 0.20, "triceps": 0.20, "forearms": 0.10, "neck": 0.20,
    },
    "badminton": {
        "calves": 0.90, "shoulders": 0.85, "quadriceps": 0.80, "triceps": 0.75,
        "hamstrings": 0.70, "forearms": 0.70, "glutes": 0.60, "core": 0.60,
        "biceps": 0.40, "back": 0.40, "chest": 0.30, "neck": 0.20,
    },
    "basketball": {
        "calves": 0.95, "quadriceps": 0.90, "glutes": 0.85, "hamstrings": 0.70,
        "core": 0.55, "shoulders": 0.55, "back": 0.40, "triceps": 0.40,
        "biceps": 0.35, "forearms": 0.35, "chest": 0.30, "neck": 0.15,
    },
    "table_tennis": {
        "forearms": 0.85, "shoulders": 0.85, "triceps": 0.75, "core": 0.60,
        "back": 0.50, "calves": 0.50, "biceps": 0.45, "quadriceps": 0.45,
        "chest": 0.35, "hamstrings": 0.35, "glutes": 0.30, "neck": 0.20,
    },
    "volleyball": {
        "calves": 0.95, "quadriceps": 0.90, "shoulders": 0.85, "glutes": 0.85,
        "triceps": 0.80, "hamstrings": 0.75, "core": 0.60, "forearms": 0.55,
        "back": 0.45, "biceps": 0.40, "chest": 0.35, "neck": 0.20,
    },
    "tennis": {
        "shoulders": 0.90, "calves": 0.85, "triceps": 0.80, "forearms": 0.80,
        "quadriceps": 0.75, "hamstrings": 0.70, "glutes": 0.70, "core": 0.70,
        "biceps": 0.50, "back": 0.50, "chest": 0.40, "neck": 0.25,
    },
    "swimming": {
        "shoulders": 0.90, "chest": 0.85, "triceps": 0.85, "core": 0.80,
        "back": 0.80, "biceps": 0.70, "calves": 0.60, "forearms": 0.60,
        "quadriceps": 0.55, "glutes": 0.45, "neck": 0.40, "hamstrings": 0.40,
    },
    "cricket": {
        "shoulders": 0.75, "core": 0.70, "calves": 0.70, "hamstrings": 0.60,
        "triceps": 0.60, "forearms": 0.60, "quadriceps": 0.55, "glutes": 0.55,
        "back": 0.45, "biceps": 0.40, "chest": 0.35, "neck": 0.35,
    },
    "golf": {
        "core": 0.75, "forearms": 0.70, "back": 0.65, "shoulders": 0.65,
        "triceps": 0.55, "biceps": 0.50, "chest": 0.45, "quadriceps": 0.45,
        "glutes": 0.40, "calves": 0.35, "hamstrings": 0.35, "neck": 0.25,
    },
    "baseball": {
        "shoulders": 0.85, "triceps": 0.80, "calves": 0.80, "forearms": 0.80,
        "hamstrings": 0.70, "core": 0.70, "quadriceps": 0.65, "glutes": 0.60,
        "back": 0.50, "biceps": 0.45, "chest": 0.40, "neck": 0.30,
    },
    "martial_arts": {
        "shoulders": 0.90, "core": 0.85, "triceps": 0.85, "calves": 0.85,
        "quadriceps": 0.80, "hamstrings": 0.75, "forearms": 0.75, "glutes": 0.70,
        "biceps": 0.70, "neck": 0.60, "back": 0.60, "chest": 0.50,
    },
    "hockey": {
        "quadriceps": 0.90, "calves": 0.90, "hamstrings": 0.85, "glutes": 0.80,
        "forearms": 0.65, "core": 0.60, "shoulders": 0.55, "back": 0.50,
        "triceps": 0.50, "biceps": 0.45, "chest": 0.30, "neck": 0.25,
    },
    "rugby": {
        "quadriceps": 0.90, "hamstrings": 0.85, "glutes": 0.85, "core": 0.85,
        "shoulders": 0.80, "calves": 0.75, "back": 0.70, "neck": 0.70,
        "chest": 0.60, "triceps": 0.60, "biceps": 0.55, "forearms": 0.55,
    },
    "handball": {
        "shoulders": 0.90, "calves": 0.90, "triceps": 0.85, "quadriceps": 0.85,
        "hamstrings": 0.75, "glutes": 0.75, "core": 0.70, "forearms": 0.70,
        "back": 0.50, "biceps": 0.50, "chest": 0.45, "neck": 0.25,
    },
    "climbing": {
        "forearms": 0.95, "back": 0.90, "shoulders": 0.90, "biceps": 0.90,
        "core": 0.85, "triceps": 0.80, "chest": 0.60, "calves": 0.65,
        "quadriceps": 0.55, "glutes": 0.40, "neck": 0.30, "hamstrings": 0.40,
    },
    "ski_snowboard": {
        "quadriceps": 0.95, "glutes": 0.80, "core": 0.75, "calves": 0.70,
        "hamstrings": 0.70, "forearms": 0.55, "back": 0.45, "shoulders": 0.45,
        "triceps": 0.40, "biceps": 0.35, "chest": 0.35, "neck": 0.30,
    },
    "cycling": {
        "quadriceps": 0.95, "glutes": 0.85, "calves": 0.70, "hamstrings": 0.60,
        "core": 0.50, "back": 0.45, "forearms": 0.45, "triceps": 0.35,
        "biceps": 0.30, "shoulders": 0.30, "neck": 0.30, "chest": 0.20,
    },
    "other": {group: 0.40 for group in MUSCLE_GROUPS},
}


def upgrade() -> None:
    op.create_table(
        "discipline_muscle_load",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("discipline", sa.String(length=40), nullable=False, index=True),
        sa.Column("muscle_group", sa.String(length=40), nullable=False),
        sa.Column("load", sa.Float(), nullable=False),
        sa.UniqueConstraint(
            "discipline", "muscle_group", name="uq_discipline_muscle_group"
        ),
    )
    op.create_table(
        "daily_readiness",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("sleep_hours", sa.Float(), nullable=True),
        sa.Column("doms", sa.Integer(), nullable=True),
        sa.Column("rest_day", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "date", name="uq_user_readiness_date"),
    )

    loads_table = sa.table(
        "discipline_muscle_load",
        sa.column("id", sa.Uuid()),
        sa.column("discipline", sa.String()),
        sa.column("muscle_group", sa.String()),
        sa.column("load", sa.Float()),
    )
    op.bulk_insert(
        loads_table,
        [
            {
                "id": uuid.uuid4(),
                "discipline": discipline,
                "muscle_group": group,
                "load": weight,
            }
            for discipline, groups in MUSCLE_LOAD_DEFAULT.items()
            for group, weight in groups.items()
        ],
    )


def downgrade() -> None:
    op.drop_table("daily_readiness")
    op.drop_table("discipline_muscle_load")
