"""add discipline catalog metadata (category, kind) + muscle_load FK

Revision ID: u7v8w9x0y1z2
Revises: t1u2v3w4x5y6
Create Date: 2026-08-11 10:00:00.000000

Cierra la deuda de catalogo de disciplinas:

- Los `normalized_name` en espanol (gimnasio, boxeo, ciclismo, natacion,
  otro) pasan a codigos canonicos en ingles (gym, boxing, cycling, swimming,
  other) coherentes con `discipline_muscle_load` y los demas modulos.
- Se amplia el catalogo a las 22 disciplinas del sistema (fuente:
  `app.analytics.discipline_seed.DISCIPLINE_SEED`) con `met`, `category`
  (tipo de deporte) y `kind` (gym / cardio).
- `discipline_muscle_load.discipline` (string) migra a `discipline_id` (FK)
  con backfill: las cargas ya referencian los codigos ingleses, por lo que el
  join contra `discipline.normalized_name` mapea las 264 filas existentes.
"""
import uuid

import sqlalchemy as sa
from sqlalchemy.sql import bindparam

from alembic import op
from app.analytics.discipline_seed import DISCIPLINE_SEED

revision: str = "u7v8w9x0y1z2"
down_revision: str | None = "t1u2v3w4x5y6"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None

# Mapeo ES -> EN de las disciplinas ya sembradas por q1r2s3t4u5v6.
_ES_TO_EN: dict[str, str] = {
    "gimnasio": "gym",
    "boxeo": "boxing",
    "ciclismo": "cycling",
    "natacion": "swimming",
    "otro": "other",
}
_EN_TO_ES: dict[str, str] = {v: k for k, v in _ES_TO_EN.items()}


def _rename_normalized(forward: bool) -> None:
    mapping = _ES_TO_EN if forward else _EN_TO_ES
    for old, new in mapping.items():
        op.execute(
            sa.text(
                "UPDATE discipline SET normalized_name = :new "
                "WHERE normalized_name = :old"
            ).bindparams(bindparam("new", new), bindparam("old", old))
        )


def _upsert_catalog() -> None:
    conn = op.get_bind()
    for name, code, met, category, kind in DISCIPLINE_SEED:
        row = conn.execute(
            sa.text("SELECT id FROM discipline WHERE normalized_name = :code"),
            {"code": code},
        ).first()
        if row:
            conn.execute(
                sa.text(
                    "UPDATE discipline SET name = :name, met = :met, "
                    "category = :category, kind = :kind "
                    "WHERE id = :id"
                ),
                {"name": name, "met": met, "category": category, "kind": kind, "id": row[0]},
            )
        else:
            conn.execute(
                sa.text(
                    "INSERT INTO discipline "
                    "(id, name, normalized_name, met, category, kind, created_at) "
                    "VALUES (:id, :name, :code, :met, :category, :kind, now())"
                ),
                {
                    "id": uuid.uuid4(),
                    "name": name,
                    "code": code,
                    "met": met,
                    "category": category,
                    "kind": kind,
                },
            )


def upgrade() -> None:
    _rename_normalized(forward=True)

    op.add_column(
        "discipline",
        sa.Column("category", sa.String(length=30), nullable=False, server_default="otros"),
    )
    op.add_column(
        "discipline",
        sa.Column("kind", sa.String(length=10), nullable=False, server_default="cardio"),
    )

    _upsert_catalog()

    # --- discipline_muscle_load: string discipline -> FK discipline_id ---
    op.add_column(
        "discipline_muscle_load",
        sa.Column("discipline_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_discipline_muscle_load_discipline",
        "discipline_muscle_load",
        "discipline",
        ["discipline_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.execute(
        sa.text(
            "UPDATE discipline_muscle_load AS dml SET discipline_id = d.id "
            "FROM discipline AS d WHERE d.normalized_name = dml.discipline"
        )
    )
    op.execute(
        sa.text(
            "UPDATE discipline_muscle_load SET discipline_id = "
            "(SELECT id FROM discipline WHERE normalized_name = 'other') "
            "WHERE discipline_id IS NULL"
        )
    )
    op.alter_column("discipline_muscle_load", "discipline_id", nullable=False)

    op.drop_index("ix_discipline_muscle_load_discipline", table_name="discipline_muscle_load")
    op.drop_constraint(
        "uq_discipline_muscle_group", "discipline_muscle_load", type_="unique"
    )
    op.drop_column("discipline_muscle_load", "discipline")

    op.create_unique_constraint(
        "uq_discipline_muscle_group", "discipline_muscle_load", ["discipline_id", "muscle_group"]
    )
    op.create_index(
        "ix_discipline_muscle_load_discipline_id",
        "discipline_muscle_load",
        ["discipline_id"],
    )


def downgrade() -> None:
    # --- discipline_muscle_load: vuelve a string discipline ---
    op.add_column(
        "discipline_muscle_load",
        sa.Column("discipline", sa.String(length=40), nullable=True, index=True),
    )
    op.execute(
        sa.text(
            "UPDATE discipline_muscle_load AS dml SET discipline = d.normalized_name "
            "FROM discipline AS d WHERE d.id = dml.discipline_id"
        )
    )
    op.alter_column("discipline_muscle_load", "discipline", nullable=False)

    op.drop_index(
        "ix_discipline_muscle_load_discipline_id", table_name="discipline_muscle_load"
    )
    op.drop_constraint(
        "uq_discipline_muscle_group", "discipline_muscle_load", type_="unique"
    )
    op.drop_constraint(
        "fk_discipline_muscle_load_discipline",
        "discipline_muscle_load",
        type_="foreignkey",
    )
    op.drop_column("discipline_muscle_load", "discipline_id")

    op.create_unique_constraint(
        "uq_discipline_muscle_group", "discipline_muscle_load", ["discipline", "muscle_group"]
    )

    # --- discipline: quitar metadata y restaurar normalized_name ES ---
    op.drop_column("discipline", "kind")
    op.drop_column("discipline", "category")
    _rename_normalized(forward=False)
