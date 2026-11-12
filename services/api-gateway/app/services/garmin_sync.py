"""Sincronización con Garmin: actividades (archivo original → importador de M6.1) y salud
diaria (FC en reposo, sueño, HRV → readiness de la fatiga)."""

import logging
import statistics
from dataclasses import asdict, dataclass, field
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import crypto, garmin
from app.core.config import settings
from app.models import DailyReadiness, GarminConnection, TrainingSession, User
from app.services import activity_import

logger = logging.getLogger(__name__)

SOURCE = "garmin"
TOKEN_MARGIN = timedelta(hours=1)
OVERLAP_DAYS = 2  # se repasan los últimos días por si el reloj sincronizó tarde
HEALTH_MAX_DAYS = 28
HRV_FULL_SWING = 0.2  # ±20 % sobre la media semanal = HRV muy baja/alta
RESTING_HR_KEYS = ("restingHeartRate", "restingHeartRateValue", "restingHR")
SLEEP_SECONDS_KEYS = ("sleepTimeSeconds", "sleepTimeInSeconds", "totalSleepSeconds")
HRV_LAST_KEYS = ("lastNightAvg", "lastNight5MinHigh")
HRV_WEEKLY_KEYS = ("weeklyAvg",)


@dataclass
class SyncResult:
    imported: int = 0
    skipped: int = 0
    errors: int = 0
    health_days: int = 0
    messages: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


async def get_connection(session: AsyncSession, user_id: object) -> GarminConnection | None:
    return await session.get(GarminConnection, user_id)


async def connect(session: AsyncSession, user: User, api_key: str) -> GarminConnection:
    """Valida la clave pidiendo un token y guarda ambos cifrados."""
    token = await garmin.request_token(api_key)
    conn = await get_connection(session, user.id) or GarminConnection(user_id=user.id)
    conn.api_key_enc = crypto.encrypt(api_key)
    conn.token_enc = crypto.encrypt(token.value)
    conn.token_expires_at = token.expires_at
    conn.status = "ok"
    conn.last_error = None
    session.add(conn)
    await session.commit()
    await session.refresh(conn)
    return conn


async def _token(session: AsyncSession, conn: GarminConnection) -> str:
    expires = conn.token_expires_at
    if expires is not None and expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if conn.token_enc and expires and expires - TOKEN_MARGIN > datetime.now(UTC):
        return crypto.decrypt(conn.token_enc)
    token = await garmin.request_token(crypto.decrypt(conn.api_key_enc))
    conn.token_enc = crypto.encrypt(token.value)
    conn.token_expires_at = token.expires_at
    await session.flush()
    return token.value


def _window(conn: GarminConnection, today: date, days: int | None) -> date:
    if days is not None:
        return today - timedelta(days=days)
    if conn.last_sync_at is None:
        return today - timedelta(days=settings.garmin_history_days)
    return conn.last_sync_at.date() - timedelta(days=OVERLAP_DAYS)


async def _already_synced(session: AsyncSession, user_id: object, external_id: str) -> bool:
    found = await session.scalar(
        select(TrainingSession.id).where(
            TrainingSession.user_id == user_id,
            TrainingSession.external_source == SOURCE,
            TrainingSession.external_id == external_id,
        )
    )
    return found is not None


async def _sync_activities(
    session: AsyncSession, user: User, token: str, start: date, end: date, result: SyncResult
) -> None:
    for activity in await garmin.list_activities(token, start, end):
        external_id = f"{SOURCE}:{activity.activity_id}"
        if await _already_synced(session, user.id, external_id):
            result.skipped += 1
            continue
        try:
            filename, content = await garmin.download_activity(token, activity.activity_id)
        except garmin.GarminAuthError:
            raise
        except garmin.GarminError as exc:
            result.errors += 1
            result.messages.append(f"{activity.name or activity.activity_id}: {exc}")
            continue
        imported = await activity_import.import_file(
            session, user, filename, content, source=SOURCE, external_id=external_id
        )
        if imported.status == "imported":
            result.imported += 1
        elif imported.status in ("duplicate", "overlap"):
            result.skipped += 1  # ya estaba (subida a mano o registrada)
        else:
            result.errors += 1
            result.messages.append(f"{activity.name or activity.activity_id}: {imported.message}")


def hrv_score(last_night: float | None, weekly: float | None) -> float | None:
    """HRV de anoche frente a la media semanal → 0-1 (0,5 = normal)."""
    if not last_night or not weekly:
        return None
    ratio = last_night / weekly
    return round(min(1.0, max(0.0, 0.5 + (ratio - 1) / (2 * HRV_FULL_SWING))), 2)


def health_by_day(summaries: object, sleep: object, hrv: object) -> dict[date, dict[str, float]]:
    days: dict[date, dict[str, float]] = {}

    def put(record: dict[str, object], key: str, value: float | None) -> None:
        day = garmin.record_date(record)
        if day is not None and value is not None:
            days.setdefault(day, {})[key] = value

    for record in garmin.records(summaries):
        put(record, "resting_hr", garmin.find(record, RESTING_HR_KEYS))
    for record in garmin.records(sleep):
        seconds = garmin.find(record, SLEEP_SECONDS_KEYS)
        put(record, "sleep_hours", round(seconds / 3600, 2) if seconds else None)
    for record in garmin.records(hrv):
        score = hrv_score(garmin.find(record, HRV_LAST_KEYS), garmin.find(record, HRV_WEEKLY_KEYS))
        put(record, "hrv_score", score)
    return days


async def _sync_health(
    session: AsyncSession, user: User, token: str, start: date, end: date, result: SyncResult
) -> None:
    start = max(start, end - timedelta(days=HEALTH_MAX_DAYS - 1))
    payloads: list[object] = []
    for fetch in (garmin.daily_summaries, garmin.sleep_summaries, garmin.hrv_summaries):
        try:
            payloads.append(await fetch(token, start, end))
        except garmin.GarminAuthError:
            raise
        except garmin.GarminError as exc:
            payloads.append(None)
            result.messages.append(f"Salud ({fetch.__name__}): {exc}")
    days = health_by_day(*payloads)
    if not days:
        return
    existing = {
        r.date: r
        for r in await session.scalars(
            select(DailyReadiness).where(
                DailyReadiness.user_id == user.id, DailyReadiness.date.in_(list(days))
            )
        )
    }
    for day, values in days.items():
        row = existing.get(day) or DailyReadiness(user_id=user.id, date=day)
        # Solo los datos del reloj: las agujetas y el día de descanso los pone el usuario.
        for key, value in values.items():
            setattr(row, key, value)
        session.add(row)
    result.health_days = len(days)
    recent = [v["resting_hr"] for d, v in sorted(days.items())[-7:] if "resting_hr" in v]
    if recent and user.resting_hr is None:
        user.resting_hr = round(statistics.median(recent))


async def sync_user(
    session: AsyncSession, user: User, conn: GarminConnection, *, days: int | None = None
) -> SyncResult:
    result = SyncResult()
    today = datetime.now(UTC).date()
    start = _window(conn, today, days)
    try:
        token = await _token(session, conn)
        await _sync_activities(session, user, token, start, today, result)
        await _sync_health(session, user, token, start, today, result)
    except garmin.GarminAuthError as exc:
        await session.rollback()
        conn.status, conn.last_error = "error", str(exc)
        conn.token_enc = None
        session.add(conn)
        await session.commit()
        raise
    except garmin.GarminError as exc:
        await session.rollback()
        conn.status, conn.last_error = "error", str(exc)
        session.add(conn)
        await session.commit()
        raise
    conn.status = "ok"
    conn.last_error = None
    conn.last_sync_at = datetime.now(UTC)
    conn.last_result = result.as_dict()
    session.add(conn)
    await session.commit()
    return result


async def sync_all(session: AsyncSession) -> int:
    """Sondeo periódico: sincroniza todas las conexiones activas. Devuelve cuántas fueron bien."""
    ok = 0
    conns = list(await session.scalars(select(GarminConnection)))
    for conn in conns:
        user = await session.get(User, conn.user_id)
        if user is None:
            continue
        try:
            await sync_user(session, user, conn)
            ok += 1
        except garmin.GarminError as exc:
            logger.warning("Sincronización de Garmin fallida para %s: %s", conn.user_id, exc)
    return ok
