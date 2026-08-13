"""add muscle + exercise_muscle tables and scale exercise catalog

Revision ID: r5s6t7u8v9w0
Revises: q1r2s3t4u5v6
Create Date: 2026-08-10 12:00:00.000000

Introduce la estructura relacional escalable del catalogo:
- `muscle`: catalogo canonico de musculos (19), cada uno con `rollup_code`
  que lo agrupa en los 12 grupos de fatiga del sistema.
- `exercise_muscle`: relacion N:M ejercicio <-> musculo con `activation`
  (0-1, los primarios pesan mas) para que cada ejercicio involucre uno o
  varios musculos sin fatigarlos a todos por igual.
- `exercise_catalog.images` (rutas relativas a free-exercise-db) y
  `details` (metadatos de fuente: categoria, equipo, instrucciones...).
- `exercise_catalog.muscle_map` se mantiene como cache desnormalizada
  (rollup por grupo) para no alterar las analiticas existentes.

Datos: importa ~800 ejercicios desde `data/exercises.json` (free-exercise-db,
dominio publico) y hace backfill de las relaciones de los 37 ejercicios
curados preexistentes.
"""
import uuid
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op
from app.analytics.catalog_seed import (
    MUSCLE_SEED,
    load_free_exercise_db,
    muscle_links_from_map,
)

revision: str = "r5s6t7u8v9w0"
down_revision: str | None = "q1r2s3t4u5v6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "exercises.json"


def _muscle_table() -> sa.Table:
    return sa.table(
        "muscle",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("label", sa.String()),
        sa.column("rollup_code", sa.String()),
    )


def _catalog_table() -> sa.Table:
    return sa.table(
        "exercise_catalog",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("normalized_name", sa.String()),
        sa.column("exercise_type", sa.String()),
        sa.column("muscle_map", JSONB()),
        sa.column("uses_bodyweight", sa.Boolean()),
        sa.column("unilateral", sa.Boolean()),
        sa.column("images", JSONB()),
        sa.column("details", JSONB()),
    )


def _exercise_muscle_table() -> sa.Table:
    return sa.table(
        "exercise_muscle",
        sa.column("id", sa.Uuid()),
        sa.column("exercise_id", sa.Uuid()),
        sa.column("muscle_id", sa.Uuid()),
        sa.column("activation", sa.Float()),
        sa.column("is_primary", sa.Boolean()),
    )


def _seed_muscles() -> dict[str, uuid.UUID]:
    rows = [
        {"id": uuid.uuid4(), "code": code, "label": label, "rollup_code": rollup}
        for code, label, rollup in MUSCLE_SEED
    ]
    op.bulk_insert(_muscle_table(), rows)
    return {row["code"]: row["id"] for row in rows}


def _insert_catalog_rows(
    entries: list[dict[str, object]],
) -> set[uuid.UUID]:
    existing = set(
        row[0]
        for row in op.get_bind().execute(
            sa.text("SELECT normalized_name FROM exercise_catalog")
        ).fetchall()
    )

    rows = [
        {
            "id": entry["id"],
            "name": entry["name"],
            "normalized_name": entry["normalized_name"],
            "exercise_type": entry["exercise_type"],
            "muscle_map": entry["muscle_map"],
            "uses_bodyweight": entry["uses_bodyweight"],
            "unilateral": entry["unilateral"],
            "images": entry["images"],
            "details": entry["details"],
        }
        for entry in entries
        if entry["normalized_name"] not in existing
    ]
    op.bulk_insert(_catalog_table(), rows)
    inserted_ids = {row["id"] for row in rows}
    print(f"[migration] catalogo: {len(rows)} ejercicios importados de free-exercise-db")
    return inserted_ids


def _insert_muscle_links(
    entries: list[dict[str, object]],
    muscle_ids: dict[str, uuid.UUID],
    inserted_ids: set[uuid.UUID],
) -> None:
    rows: list[dict[str, object]] = []
    for entry in entries:
        if entry["id"] not in inserted_ids:
            continue
        for link in entry["muscle_links"]:
            muscle_id = muscle_ids.get(link["muscle_code"])
            if muscle_id is None:
                continue
            rows.append(
                {
                    "id": uuid.uuid4(),
                    "exercise_id": entry["id"],
                    "muscle_id": muscle_id,
                    "activation": link["activation"],
                    "is_primary": link["is_primary"],
                }
            )
    if rows:
        op.bulk_insert(_exercise_muscle_table(), rows)


def _backfill_curated_links(
    muscle_ids: dict[str, uuid.UUID],
    inserted_ids: set[uuid.UUID],
) -> None:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            "SELECT id, muscle_map FROM exercise_catalog "
            "WHERE muscle_map IS NOT NULL"
        )
    ).fetchall()
    rows: list[dict[str, object]] = []
    for exercise_id, muscle_map in result:
        if exercise_id in inserted_ids:
            continue
        for link in muscle_links_from_map(muscle_map):
            muscle_id = muscle_ids.get(link["muscle_code"])
            if muscle_id is None:
                continue
            rows.append(
                {
                    "id": uuid.uuid4(),
                    "exercise_id": exercise_id,
                    "muscle_id": muscle_id,
                    "activation": link["activation"],
                    "is_primary": link["is_primary"],
                }
            )
    if rows:
        op.bulk_insert(_exercise_muscle_table(), rows)


def upgrade() -> None:
    op.create_table(
        "muscle",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column("rollup_code", sa.String(length=40), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("code", name="uq_muscle_code"),
    )
    op.create_index(op.f("ix_muscle_code"), "muscle", ["code"])
    op.create_index(op.f("ix_muscle_rollup_code"), "muscle", ["rollup_code"])

    op.create_table(
        "exercise_muscle",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "exercise_id",
            sa.Uuid(),
            sa.ForeignKey("exercise_catalog.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "muscle_id",
            sa.Uuid(),
            sa.ForeignKey("muscle.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("activation", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "exercise_id", "muscle_id", name="uq_exercise_muscle_exercise_muscle"
        ),
    )
    op.create_index(
        op.f("ix_exercise_muscle_exercise_id"),
        "exercise_muscle",
        ["exercise_id"],
    )
    op.create_index(
        op.f("ix_exercise_muscle_muscle_id"),
        "exercise_muscle",
        ["muscle_id"],
    )

    op.add_column("exercise_catalog", sa.Column("images", JSONB(), nullable=True))
    op.add_column("exercise_catalog", sa.Column("details", JSONB(), nullable=True))

    if not _DATA_FILE.exists():
        raise RuntimeError(
            f"Falta el dataset de ejercicios en {_DATA_FILE}. "
            "Descargalo desde https://raw.githubusercontent.com/yuhonas/"
            "free-exercise-db/main/dist/exercises.json"
        )
    entries = load_free_exercise_db(_DATA_FILE)
    muscle_ids = _seed_muscles()
    inserted_ids = _insert_catalog_rows(entries)
    _insert_muscle_links(entries, muscle_ids, inserted_ids)
    _backfill_curated_links(muscle_ids, inserted_ids)


def downgrade() -> None:
    op.drop_index(op.f("ix_exercise_muscle_muscle_id"), table_name="exercise_muscle")
    op.drop_index(op.f("ix_exercise_muscle_exercise_id"), table_name="exercise_muscle")
    op.drop_table("exercise_muscle")
    op.drop_index(op.f("ix_muscle_rollup_code"), table_name="muscle")
    op.drop_index(op.f("ix_muscle_code"), table_name="muscle")
    op.drop_table("muscle")
    op.drop_column("exercise_catalog", "details")
    op.drop_column("exercise_catalog", "images")
