"""add spanish translations to exercise catalog details

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-11-11

Añade `nameEs` / `instructionsEs` a `exercise_catalog.details` desde
`data/exercises_es.json` (generado con scripts/translate_catalog.py). Idempotente;
si el fichero no existe no hace nada. Se puede volver a aplicar tras regenerar
las traducciones con `alembic downgrade -1 && alembic upgrade head`.
"""

import json
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa

from alembic import op
from app.analytics.catalog_seed import (
    TRANSLATIONS_FILENAME,
    load_translations,
    translated_details,
)

revision: str = "c8d9e0f1a2b3"
down_revision: str | None = "b7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TRANSLATIONS = Path(__file__).resolve().parents[2] / "data" / TRANSLATIONS_FILENAME
_catalog = sa.table(
    "exercise_catalog", sa.column("id", sa.Uuid()), sa.column("details", sa.JSON())
)


def _rows(bind: sa.Connection) -> list[tuple[object, dict[str, object]]]:
    result = bind.execute(sa.select(_catalog.c.id, _catalog.c.details))
    rows: list[tuple[object, dict[str, object]]] = []
    for row_id, details in result:
        if isinstance(details, str):
            details = json.loads(details)
        if isinstance(details, dict):
            rows.append((row_id, details))
    return rows


def upgrade() -> None:
    translations = load_translations(_TRANSLATIONS)
    if not translations:
        return
    bind = op.get_bind()
    for row_id, details in _rows(bind):
        merged = translated_details(details, translations)
        if merged is not None:
            bind.execute(
                _catalog.update().where(_catalog.c.id == row_id).values(details=merged)
            )


def downgrade() -> None:
    bind = op.get_bind()
    for row_id, details in _rows(bind):
        if "nameEs" in details or "instructionsEs" in details:
            cleaned = {k: v for k, v in details.items() if k not in ("nameEs", "instructionsEs")}
            bind.execute(
                _catalog.update().where(_catalog.c.id == row_id).values(details=cleaned)
            )
