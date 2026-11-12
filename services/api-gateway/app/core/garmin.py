"""Cliente de la API personal de Garmin Connect (solo lectura de los datos del propio usuario).

Referencia: cliente oficial github.com/garmin/connect-personal-api-python.
- Token: POST /personalapitoken-service/personal-api/personal-api-key/token con
  `Authorization: ApiKey <clave>`; la respuesta es el JWT en texto plano (caduca a las 24 h).
- Datos: GET con `Authorization: Bearer <token>`.
Los esquemas de respuesta no están documentados en el cliente, así que la lectura es tolerante
(ver `records` y `find`).
"""

import base64
import io
import json
import zipfile
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, date, datetime

import httpx

from app.core.config import settings

TOKEN_PATH = "/personalapitoken-service/personal-api/personal-api-key/token"
SEARCH_PATH = "/activitylist-service/activities/search/activities"
DOWNLOAD_PATH = "/download-service/files/activity/{activity_id}"
DAILY_SUMMARIES_PATH = "/usersummary-service/v2/dailysummaries"
SLEEP_PATH = "/sleep-service/sleep/dailySleepSummariesByDate"
HRV_PATH = "/hrv-service/hrv/daily/{start}/{end}"
PAGE_SIZE = 50
MAX_PAGES = 20
DATE_KEYS = ("calendarDate", "summaryDate", "date")


class GarminError(Exception):
    """Fallo al hablar con Garmin (red, respuesta inesperada)."""


class GarminAuthError(GarminError):
    """Clave inválida, revocada o caducada."""


@dataclass(frozen=True)
class GarminToken:
    value: str
    expires_at: datetime


@dataclass(frozen=True)
class GarminActivity:
    activity_id: str
    name: str | None
    type_key: str | None
    start: datetime | None


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.garmin_base_url, timeout=settings.garmin_timeout_seconds
    )


def _raise_for(response: httpx.Response) -> None:
    if response.status_code in (401, 403):
        raise GarminAuthError("Garmin ha rechazado la clave (inválida, revocada o caducada)")
    if response.status_code >= 400:
        raise GarminError(f"Garmin respondió {response.status_code}")


def token_expiry(jwt: str) -> datetime:
    """Caducidad del JWT (claim `exp`), leída sin verificar la firma."""
    try:
        payload = jwt.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        return datetime.fromtimestamp(float(claims["exp"]), tz=UTC)
    except (IndexError, KeyError, ValueError, TypeError) as exc:
        raise GarminError("Token de Garmin con formato inesperado") from exc


async def request_token(api_key: str) -> GarminToken:
    try:
        async with _client() as client:
            response = await client.post(
                TOKEN_PATH, headers={"Accept": "*/*", "Authorization": f"ApiKey {api_key}"}
            )
    except httpx.HTTPError as exc:
        raise GarminError(f"No se pudo contactar con Garmin: {exc}") from exc
    _raise_for(response)
    value = response.text.strip()
    return GarminToken(value=value, expires_at=token_expiry(value))


async def _get(token: str, path: str, params: dict[str, str | int] | None = None) -> object:
    try:
        async with _client() as client:
            response = await client.get(
                path,
                params=params,
                headers={"Accept": "application/json", "Authorization": f"Bearer {token}"},
            )
    except httpx.HTTPError as exc:
        raise GarminError(f"No se pudo contactar con Garmin: {exc}") from exc
    _raise_for(response)
    if response.status_code == 204 or not response.content:
        return None  # sin datos para ese rango (p. ej. VFC si el reloj no la mide)
    try:
        return response.json()
    except ValueError as exc:
        raise GarminError("Respuesta de Garmin que no es JSON") from exc


def _parse_start(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _activity(item: dict[str, object]) -> GarminActivity | None:
    activity_id = item.get("activityId")
    if activity_id is None:
        return None
    kind = item.get("activityType")
    type_key = kind.get("typeKey") if isinstance(kind, dict) else None
    name = item.get("activityName")
    return GarminActivity(
        activity_id=str(activity_id),
        name=name if isinstance(name, str) else None,
        type_key=type_key if isinstance(type_key, str) else None,
        start=_parse_start(item.get("startTimeGMT") or item.get("startTimeLocal")),
    )


async def list_activities(token: str, start: date, end: date) -> list[GarminActivity]:
    found: list[GarminActivity] = []
    for page in range(MAX_PAGES):
        payload = await _get(
            token,
            SEARCH_PATH,
            {
                "start": page * PAGE_SIZE,
                "limit": PAGE_SIZE,
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
            },
        )
        items = payload
        if isinstance(payload, dict):
            items = payload.get("activities") or payload.get("activityList") or []
        if not isinstance(items, list):
            raise GarminError("Listado de actividades de Garmin con formato inesperado")
        found.extend(a for a in (_activity(i) for i in items if isinstance(i, dict)) if a)
        if len(items) < PAGE_SIZE:
            break
    return found


def unpack_activity_file(activity_id: str, content: bytes) -> tuple[str, bytes]:
    """Garmin entrega el archivo original dentro de un ZIP; si no es ZIP se usa tal cual."""
    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            members = [m for m in archive.infolist() if not m.is_dir()]
            if not members:
                raise GarminError("ZIP de actividad vacío")
            member = next(
                (m for m in members if m.filename.lower().endswith((".fit", ".tcx", ".gpx"))),
                members[0],
            )
            return member.filename.rsplit("/", 1)[-1], archive.read(member)
    return f"{activity_id}.fit", content


async def download_activity(token: str, activity_id: str) -> tuple[str, bytes]:
    try:
        async with _client() as client:
            response = await client.get(
                DOWNLOAD_PATH.format(activity_id=activity_id),
                headers={
                    "Accept": "application/zip, application/x-zip-compressed, "
                    "application/octet-stream",
                    "Authorization": f"Bearer {token}",
                },
            )
    except httpx.HTTPError as exc:
        raise GarminError(f"No se pudo descargar la actividad: {exc}") from exc
    _raise_for(response)
    return unpack_activity_file(activity_id, response.content)


def records(payload: object) -> Iterator[dict[str, object]]:
    """Objetos con fecha (`calendarDate`…) en cualquier nivel de la respuesta."""
    if isinstance(payload, list):
        for item in payload:
            yield from records(item)
    elif isinstance(payload, dict):
        if any(isinstance(payload.get(k), str) for k in DATE_KEYS):
            yield payload
            return
        for value in payload.values():
            if isinstance(value, (list, dict)):
                yield from records(value)


def record_date(record: dict[str, object]) -> date | None:
    for key in DATE_KEYS:
        raw = record.get(key)
        if isinstance(raw, str):
            try:
                return date.fromisoformat(raw[:10])
            except ValueError:
                return None
    return None


def find(record: object, keys: tuple[str, ...]) -> float | None:
    """Primer valor numérico con alguno de esos nombres, buscando en profundidad."""
    if isinstance(record, dict):
        for key in keys:
            value = record.get(key)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                return float(value)
        for value in record.values():
            found = find(value, keys)
            if found is not None:
                return found
    elif isinstance(record, list):
        for item in record:
            found = find(item, keys)
            if found is not None:
                return found
    return None


async def daily_summaries(token: str, start: date, end: date) -> object:
    params: dict[str, str | int] = {"startDate": start.isoformat(), "endDate": end.isoformat()}
    return await _get(token, DAILY_SUMMARIES_PATH, params)


async def sleep_summaries(token: str, start: date, end: date) -> object:
    params: dict[str, str | int] = {"startDate": start.isoformat(), "endDate": end.isoformat()}
    return await _get(token, SLEEP_PATH, params)


async def hrv_summaries(token: str, start: date, end: date) -> object:
    return await _get(token, HRV_PATH.format(start=start.isoformat(), end=end.isoformat()))
