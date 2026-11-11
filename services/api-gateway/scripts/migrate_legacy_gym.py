"""Migra sesiones de fuerza del modelo plano (`exercises`) al modelo gym (ADR-001).

Uso (desde services/api-gateway):
    .venv/Scripts/python -m scripts.migrate_legacy_gym
Es idempotente: se puede ejecutar varias veces.
"""

import asyncio

from app.core.database import async_session_factory
from app.services.session_ingest import migrate_legacy_strength_sessions


async def main() -> None:
    async with async_session_factory() as session:
        migrated = await migrate_legacy_strength_sessions(session)
    print(f"Sesiones migradas al modelo gym: {migrated}")


if __name__ == "__main__":
    asyncio.run(main())
