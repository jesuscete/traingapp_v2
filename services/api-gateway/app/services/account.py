"""Exportación (RGPD: portabilidad) y borrado de la cuenta del usuario."""

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import ColumnElement, Table, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base
from app.models import User

# Columnas que nunca salen en la exportación (secretos o hashes).
SECRET_COLUMNS = {
    "users": {"hashed_password", "token_version"},
    "garmin_connections": {"api_key_enc", "token_enc"},
    "auth_sessions": {"token_hash"},
}
MAX_DEPTH = 6


@dataclass
class OwnedRows:
    table: Table
    where: ColumnElement[bool]
    rows: list[dict[str, object]]


def _jsonable(value: object) -> object:
    if isinstance(value, (uuid.UUID, Decimal)):
        return str(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


async def _select(session: AsyncSession, table: Table, where: ColumnElement[bool]) -> OwnedRows:
    result = await session.execute(select(table).where(where))
    return OwnedRows(table, where, [dict(r) for r in result.mappings()])


async def owned_rows(session: AsyncSession, user_id: uuid.UUID) -> dict[str, OwnedRows]:
    """Filas del usuario: tablas con `user_id` y sus hijas siguiendo las claves foráneas."""
    owned: dict[str, OwnedRows] = {}
    for table in Base.metadata.sorted_tables:
        if "user_id" in table.c and table.name != "users":
            found = await _select(session, table, table.c.user_id == user_id)
            if found.rows:
                owned[table.name] = found
    frontier = set(owned)
    for _ in range(MAX_DEPTH):
        new: set[str] = set()
        for table in Base.metadata.sorted_tables:
            if table.name in owned or table.name == "users" or "user_id" in table.c:
                continue
            for fk in table.foreign_keys:
                parent = fk.column.table.name
                if parent not in frontier or fk.column.name != "id":
                    continue
                ids = [r["id"] for r in owned[parent].rows]
                found = await _select(session, table, fk.parent.in_(ids))
                if found.rows:
                    owned[table.name] = found
                    new.add(table.name)
                break
        if not new:
            break
        frontier = new
    return owned


async def export_user(session: AsyncSession, user: User) -> dict[str, object]:
    users_table = Base.metadata.tables["users"]
    me = await _select(session, users_table, users_table.c.id == user.id)
    data: dict[str, object] = {}
    for name, found in {"users": me, **await owned_rows(session, user.id)}.items():
        hidden = SECRET_COLUMNS.get(name, set())
        data[name] = [
            {k: _jsonable(v) for k, v in row.items() if k not in hidden} for row in found.rows
        ]
    return data


async def delete_user(session: AsyncSession, user: User) -> None:
    """Borra la cuenta y todas sus filas (de hijas a padres; en Postgres además hay CASCADE)."""
    owned = await owned_rows(session, user.id)
    for table in reversed(Base.metadata.sorted_tables):
        if table.name in owned:
            await session.execute(delete(table).where(owned[table.name].where))
    await session.delete(user)
    await session.commit()
