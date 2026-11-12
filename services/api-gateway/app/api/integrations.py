from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core import garmin
from app.core.database import get_db
from app.models import GarminConnection, User
from app.schemas.session import CamelModel
from app.services import garmin_sync

router = APIRouter(prefix="/integrations", tags=["integrations"])
Db = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
AUTO_SYNC_AFTER = timedelta(minutes=15)


class GarminKeyIn(CamelModel):
    api_key: str = Field(min_length=10, max_length=4096)


class GarminStatusOut(CamelModel):
    connected: bool
    status: str | None = None
    last_sync_at: datetime | None = None
    last_error: str | None = None
    last_result: dict[str, object] | None = None
    token_expires_at: datetime | None = None


class GarminSyncOut(CamelModel):
    imported: int
    skipped: int
    errors: int
    health_days: int
    messages: list[str]
    status: GarminStatusOut


def _status(conn: GarminConnection | None) -> GarminStatusOut:
    if conn is None:
        return GarminStatusOut(connected=False)
    return GarminStatusOut(
        connected=True,
        status=conn.status,
        last_sync_at=conn.last_sync_at,
        last_error=conn.last_error,
        last_result=conn.last_result,
        token_expires_at=conn.token_expires_at,
    )


async def _require(db: AsyncSession, user: User) -> GarminConnection:
    conn = await garmin_sync.get_connection(db, user.id)
    if conn is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Garmin no conectado")
    return conn


@router.get("/garmin", response_model=GarminStatusOut)
async def garmin_status(db: Db, user: CurrentUser) -> GarminStatusOut:
    return _status(await garmin_sync.get_connection(db, user.id))


@router.put("/garmin", response_model=GarminStatusOut)
async def garmin_connect(body: GarminKeyIn, db: Db, user: CurrentUser) -> GarminStatusOut:
    """Guarda la clave personal de Garmin tras comprobar que funciona."""
    try:
        conn = await garmin_sync.connect(db, user, body.api_key.strip())
    except garmin.GarminAuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except garmin.GarminError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    return _status(conn)


@router.delete("/garmin", status_code=status.HTTP_204_NO_CONTENT)
async def garmin_disconnect(db: Db, user: CurrentUser) -> None:
    """Borra la clave y el token. Las actividades ya importadas se conservan."""
    conn = await _require(db, user)
    await db.delete(conn)
    await db.commit()


@router.post("/garmin/sync", response_model=GarminSyncOut)
async def garmin_sync_now(
    db: Db,
    user: CurrentUser,
    days: Annotated[int | None, Query(ge=1, le=365)] = None,
    if_stale: Annotated[bool, Query(alias="ifStale")] = False,
) -> GarminSyncOut:
    """Sincroniza ya. Con `ifStale=true` (al abrir la app) solo si hace >15 min de la última."""
    conn = await _require(db, user)
    last = conn.last_sync_at
    if last is not None and last.tzinfo is None:
        last = last.replace(tzinfo=UTC)
    if if_stale and last is not None and datetime.now(UTC) - last < AUTO_SYNC_AFTER:
        empty = garmin_sync.SyncResult()
        return GarminSyncOut(**empty.as_dict(), status=_status(conn))
    try:
        result = await garmin_sync.sync_user(db, user, conn, days=days)
    except garmin.GarminError as exc:
        code = (
            status.HTTP_400_BAD_REQUEST
            if isinstance(exc, garmin.GarminAuthError)
            else status.HTTP_502_BAD_GATEWAY
        )
        raise HTTPException(status_code=code, detail=str(exc)) from exc
    return GarminSyncOut(**result.as_dict(), status=_status(conn))
