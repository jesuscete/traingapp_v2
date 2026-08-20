"""add explosive/power exercises to canonical exercise catalog

Revision ID: a1b2c3d4e5f7
Revises: z8y7x6w5v4u3
Create Date: 2026-08-16 14:00:00.000000

Amplia el catalogo curado con ejercicios de potencia/explosividad en espanol
(press empujadora, cargada de potencia, saltos, lanzamiento de balon, sprints)
para que los perfiles de rendimiento deportivo (explosividad, fuerza) tengan
opciones reales que elegir en la generacion de planes con IA. Insertar solo
los que no existan ya (diff por normalized_name) e indexar sus relaciones
`exercise_muscle`.
"""
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op
from app.analytics.catalog_seed import muscle_links_from_map
from app.analytics.exercise_seed import EXERCISE_CATALOG_SEED

revision: str = "a1b2c3d4e5f7"
down_revision: str | None = "z8y7x6w5v4u3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(
        row[0]
        for row in bind.execute(
            sa.text("SELECT normalized_name FROM exercise_catalog")
        ).fetchall()
    )
    new_entries = [
        entry
        for entry in EXERCISE_CATALOG_SEED
        if entry["normalized_name"] not in existing
    ]

    muscle_ids = {
        row[0]: row[1]
        for row in bind.execute(sa.text("SELECT code, id FROM muscle")).fetchall()
    }

    rows = []
    for entry in new_entries:
        entry_id = uuid.uuid4()
        rows.append(
            {
                "id": entry_id,
                "name": entry["name"],
                "normalized_name": entry["normalized_name"],
                "exercise_type": entry["exercise_type"],
                "muscle_map": entry["muscles"],
                "uses_bodyweight": entry.get("uses_bodyweight", False),
                "unilateral": entry.get("unilateral", False),
            }
        )
    op.bulk_insert(_catalog_table(), rows)

    links: list[dict[str, object]] = []
    for entry, row in zip(new_entries, rows):
        for link in muscle_links_from_map(entry["muscles"]):
            muscle_id = muscle_ids.get(link["muscle_code"])
            if muscle_id is None:
                continue
            links.append(
                {
                    "id": uuid.uuid4(),
                    "exercise_id": row["id"],
                    "muscle_id": muscle_id,
                    "activation": link["activation"],
                    "is_primary": link["is_primary"],
                }
            )
    if links:
        op.bulk_insert(_exercise_muscle_table(), links)

    print(f"[migration] catalogo: {len(rows)} ejercicios explosivos anadidos")


def downgrade() -> None:
    normalized_names = [
        entry["normalized_name"]
        for entry in EXERCISE_CATALOG_SEED
        if entry["normalized_name"]
        in {
            "press empujadora",
            "landmine press",
            "cargada de potencia",
            "balanceo con kettlebell",
            "saltos al cajon",
            "saltos verticales",
            "lanzamiento de balon medicinal",
            "sprints",
        }
    ]
    bind = op.get_bind()
    ids = [
        row[0]
        for row in bind.execute(
            sa.text(
                "SELECT id FROM exercise_catalog "
                "WHERE normalized_name = ANY(:names)"
            ),
            {"names": normalized_names},
        ).fetchall()
    ]
    if ids:
        bind.execute(
            sa.text(
                "DELETE FROM exercise_muscle WHERE exercise_id = ANY(:ids)"
            ),
            {"ids": ids},
        )
        bind.execute(
            sa.text("DELETE FROM exercise_catalog WHERE id = ANY(:ids)"),
            {"ids": ids},
        )
