"""add training_prompt + discipline_training_prompt tables

Revision ID: z8y7x6w5v4u3
Revises: u7v8w9x0y1z2
Create Date: 2026-08-15 12:00:00.000000

Crea el modelo de perfiles de entrenamiento con su prompt asociado (fuente de
verdad para que la IA base su recomendacion de rutina en las demandas del
deporte) y la asignacion disciplina -> perfil:

- `training_prompt`: perfil (fuerza, explosividad, hipertrofia, resistencia,
  balanced) con la plantilla de prompt. `is_default` marca el fallback
  (rutina equilibrada) para deportes sin perfil asignado.
- `discipline_training_prompt`: N disciplinas -> 1 perfil. Cada disciplina
  tiene como mucho un perfil (unique sobre discipline_id).

Se siembran los 5 perfiles y las asignaciones del catalogo de disciplinas
desde `app.analytics.prompt_seed`.
"""
import uuid

import sqlalchemy as sa

from alembic import op
from app.analytics.prompt_seed import (
    DISCIPLINE_PROMPT_SEED,
    TRAINING_PROMPT_SEED,
)

revision: str = "z8y7x6w5v4u3"
down_revision: str | None = "u7v8w9x0y1z2"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None


def _seed_prompts_and_mapping() -> None:
    conn = op.get_bind()
    prompt_ids: dict[str, uuid.UUID] = {}
    for code, name, description, is_default, system_prompt in TRAINING_PROMPT_SEED:
        prompt_id = uuid.uuid4()
        prompt_ids[code] = prompt_id
        conn.execute(
            sa.text(
                "INSERT INTO training_prompt "
                "(id, code, name, description, system_prompt, is_default, active, "
                "created_at, updated_at) "
                "VALUES (:id, :code, :name, :description, :system_prompt, :is_default, "
                ":active, now(), now())"
            ),
            {
                "id": prompt_id,
                "code": code,
                "name": name,
                "description": description,
                "system_prompt": system_prompt,
                "is_default": is_default,
                "active": True,
            },
        )
    for discipline_name, prompt_code in DISCIPLINE_PROMPT_SEED:
        row = conn.execute(
            sa.text(
                "SELECT id FROM discipline WHERE normalized_name = :code"
            ),
            {"code": discipline_name},
        ).first()
        if row is None:
            continue
        conn.execute(
            sa.text(
                "INSERT INTO discipline_training_prompt "
                "(id, discipline_id, training_prompt_id) "
                "VALUES (:id, :discipline_id, :training_prompt_id)"
            ),
            {
                "id": uuid.uuid4(),
                "discipline_id": row[0],
                "training_prompt_id": prompt_ids[prompt_code],
            },
        )


def upgrade() -> None:
    op.create_table(
        "training_prompt",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("system_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_training_prompt_code", "training_prompt", ["code"], unique=True)

    op.create_table(
        "discipline_training_prompt",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "discipline_id",
            sa.Uuid(),
            sa.ForeignKey("discipline.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "training_prompt_id",
            sa.Uuid(),
            sa.ForeignKey("training_prompt.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_discipline_training_prompt_discipline_id",
        "discipline_training_prompt",
        ["discipline_id"],
        unique=True,
    )
    op.create_index(
        "ix_discipline_training_prompt_training_prompt_id",
        "discipline_training_prompt",
        ["training_prompt_id"],
    )

    _seed_prompts_and_mapping()


def downgrade() -> None:
    op.drop_index(
        "ix_discipline_training_prompt_training_prompt_id",
        table_name="discipline_training_prompt",
    )
    op.drop_index(
        "ix_discipline_training_prompt_discipline_id",
        table_name="discipline_training_prompt",
    )
    op.drop_table("discipline_training_prompt")
    op.drop_index("ix_training_prompt_code", table_name="training_prompt")
    op.drop_table("training_prompt")
