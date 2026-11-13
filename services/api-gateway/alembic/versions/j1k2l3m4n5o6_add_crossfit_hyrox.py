"""CrossFit y HYROX: disciplinas, carga muscular y movimientos que faltaban en el catálogo

Revision ID: j1k2l3m4n5o6
Revises: i0j1k2l3m4n5
Create Date: 2026-11-13

Inserta solo lo que no existe (disciplina por normalized_name, ejercicio por
normalized_name), así que es seguro aunque alguien los haya creado antes.
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op
from app.analytics.catalog import normalize_exercise_name
from app.analytics.catalog_seed import muscle_links_from_map
from app.analytics.discipline_seed import DISCIPLINE_SEED
from app.analytics.fatigue import MUSCLE_LOAD_DEFAULT
from app.analytics.wod_exercise_seed import WOD_EXERCISE_SEED

revision: str = "j1k2l3m4n5o6"
down_revision: str | None = "i0j1k2l3m4n5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_DISCIPLINES = ("crossfit", "hyrox")
SOURCE = "crossfit_hyrox"


def upgrade() -> None:
    bind = op.get_bind()

    # --- Disciplinas + carga muscular (fatiga) ---
    existing = {r[0] for r in bind.execute(sa.text("SELECT normalized_name FROM discipline"))}
    discipline = sa.table(
        "discipline",
        sa.column("id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("normalized_name", sa.String()),
        sa.column("met", sa.Float()),
        sa.column("category", sa.String()),
        sa.column("kind", sa.String()),
    )
    load = sa.table(
        "discipline_muscle_load",
        sa.column("id", sa.Uuid()),
        sa.column("discipline_id", sa.Uuid()),
        sa.column("muscle_group", sa.String()),
        sa.column("load", sa.Float()),
    )
    disciplines, loads = [], []
    for name, normalized, met, category, kind in DISCIPLINE_SEED:
        if normalized not in NEW_DISCIPLINES or normalized in existing:
            continue
        discipline_id = uuid.uuid4()
        disciplines.append(
            {
                "id": discipline_id,
                "name": name,
                "normalized_name": normalized,
                "met": met,
                "category": category,
                "kind": kind,
            }
        )
        for group, value in MUSCLE_LOAD_DEFAULT[normalized].items():
            loads.append(
                {
                    "id": uuid.uuid4(),
                    "discipline_id": discipline_id,
                    "muscle_group": group,
                    "load": value,
                }
            )
    if disciplines:
        op.bulk_insert(discipline, disciplines)
        op.bulk_insert(load, loads)

    # --- Movimientos del catálogo ---
    names = {r[0] for r in bind.execute(sa.text("SELECT normalized_name FROM exercise_catalog"))}
    muscle_ids = dict(bind.execute(sa.text("SELECT code, id FROM muscle")).fetchall())
    catalog = sa.table(
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
    exercise_muscle = sa.table(
        "exercise_muscle",
        sa.column("id", sa.Uuid()),
        sa.column("exercise_id", sa.Uuid()),
        sa.column("muscle_id", sa.Uuid()),
        sa.column("activation", sa.Float()),
        sa.column("is_primary", sa.Boolean()),
    )
    rows, links = [], []
    for entry in WOD_EXERCISE_SEED:
        normalized = normalize_exercise_name(entry["name"])
        if normalized in names:
            continue
        exercise_id = uuid.uuid4()
        rows.append(
            {
                "id": exercise_id,
                "name": entry["name"],
                "normalized_name": normalized,
                "exercise_type": "gym",
                "muscle_map": entry["muscles"],
                "uses_bodyweight": entry["uses_bodyweight"],
                "unilateral": False,
                "images": [],
                "details": {
                    "source": SOURCE,
                    "nameEs": entry["name_es"],
                    "category": entry["category"],
                    "unit": entry["unit"],
                },
            }
        )
        for link in muscle_links_from_map(entry["muscles"]):
            muscle_id = muscle_ids.get(link["muscle_code"])
            if muscle_id is not None:
                links.append(
                    {
                        "id": uuid.uuid4(),
                        "exercise_id": exercise_id,
                        "muscle_id": muscle_id,
                        "activation": link["activation"],
                        "is_primary": link["is_primary"],
                    }
                )
    if rows:
        op.bulk_insert(catalog, rows)
    if links:
        op.bulk_insert(exercise_muscle, links)
    print(f"[migration] crossfit/hyrox: {len(disciplines)} disciplinas, {len(rows)} ejercicios")


def downgrade() -> None:
    op.execute(
        "DELETE FROM exercise_muscle WHERE exercise_id IN "
        f"(SELECT id FROM exercise_catalog WHERE details->>'source' = '{SOURCE}')"
    )
    op.execute(f"DELETE FROM exercise_catalog WHERE details->>'source' = '{SOURCE}'")
    op.execute(
        "DELETE FROM discipline_muscle_load WHERE discipline_id IN "
        "(SELECT id FROM discipline WHERE normalized_name IN ('crossfit', 'hyrox'))"
    )
    op.execute("DELETE FROM discipline WHERE normalized_name IN ('crossfit', 'hyrox')")
