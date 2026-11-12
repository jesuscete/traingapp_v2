"""Lectura de archivos de actividad (M6.1): FIT (Garmin y otros), GPX y TCX.

Convierte cualquier formato en un `ParsedActivity` común: deporte, resumen, muestras
(FC, velocidad, altitud, cadencia, potencia, distancia), vueltas y series de fuerza.
Sin BD: el servicio de importación decide cómo guardarlo.
"""

import hashlib
import io
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import UTC, datetime

import fitdecode


class ActivityFileError(ValueError):
    """Archivo ilegible o sin datos de actividad."""


@dataclass
class Sample:
    t: float  # segundos desde el inicio
    hr: float | None = None
    speed: float | None = None  # m/s
    altitude: float | None = None
    cadence: float | None = None
    power: float | None = None
    distance: float | None = None  # m acumulados


@dataclass(frozen=True)
class Lap:
    start_s: float
    duration_s: float
    distance_m: float | None
    avg_hr: float | None
    max_hr: float | None


@dataclass(frozen=True)
class StrengthSet:
    exercise: str | None
    reps: int | None
    weight_kg: float | None
    duration_s: float | None


@dataclass
class ParsedActivity:
    sport: str  # deporte de origen normalizado ("running", "cycling", "training"...)
    sub_sport: str | None
    start: datetime
    duration_s: float
    fingerprint: str  # identificador estable del archivo/actividad (deduplicación)
    distance_m: float | None = None
    ascent_m: float | None = None
    avg_hr: float | None = None
    max_hr: float | None = None
    calories: float | None = None
    avg_cadence: float | None = None
    samples: list[Sample] = field(default_factory=list)
    laps: list[Lap] = field(default_factory=list)
    strength_sets: list[StrengthSet] = field(default_factory=list)


def _hash(*parts: object) -> str:
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:24]


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _fill_summary(act: ParsedActivity) -> ParsedActivity:
    """Completa con las muestras lo que el archivo no trae en el resumen."""
    hrs = [s.hr for s in act.samples if s.hr]
    if hrs and act.avg_hr is None:
        act.avg_hr = round(sum(hrs) / len(hrs), 1)
    if hrs and act.max_hr is None:
        act.max_hr = max(hrs)
    distances = [s.distance for s in act.samples if s.distance is not None]
    if distances and act.distance_m is None:
        act.distance_m = round(max(distances), 1)
    if act.ascent_m is None:
        alts = [s.altitude for s in act.samples if s.altitude is not None]
        gain = sum(max(0.0, b - a) for a, b in zip(alts, alts[1:], strict=False))
        act.ascent_m = round(gain, 1) if alts else None
    if act.duration_s <= 0 and act.samples:
        act.duration_s = act.samples[-1].t
    return act


# --- FIT ---------------------------------------------------------------------------------


def _v(frame: fitdecode.FitDataMessage, *names: str) -> object | None:
    for name in names:
        if frame.has_field(name):
            value: object = frame.get_value(name)
            if value is not None:
                return value
    return None


def _f(value: object | None) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(str(value))
    except ValueError:
        return None


def _fit_lap(lap: dict[str, object], start: datetime) -> Lap:
    lap_start = lap.get("start")
    return Lap(
        start_s=(_aware(lap_start) - start).total_seconds()
        if isinstance(lap_start, datetime)
        else 0.0,
        duration_s=_f(lap.get("duration")) or 0.0,
        distance_m=_f(lap.get("distance")),
        avg_hr=_f(lap.get("avg_hr")),
        max_hr=_f(lap.get("max_hr")),
    )


def parse_fit(data: bytes) -> ParsedActivity:
    session: dict[str, object] = {}
    file_id: dict[str, object] = {}
    records: list[tuple[datetime, dict[str, float | None]]] = []
    laps: list[dict[str, object]] = []
    sets: list[StrengthSet] = []
    try:
        with fitdecode.FitReader(io.BytesIO(data), check_crc=fitdecode.CrcCheck.WARN) as reader:
            for frame in reader:
                if not isinstance(frame, fitdecode.FitDataMessage):
                    continue
                if frame.name == "file_id":
                    file_id = {
                        "serial": _v(frame, "serial_number"),
                        "created": _v(frame, "time_created"),
                    }
                elif frame.name == "session" and not session:
                    session = {
                        "sport": _v(frame, "sport"),
                        "sub_sport": _v(frame, "sub_sport"),
                        "start": _v(frame, "start_time"),
                        "duration": _f(_v(frame, "total_timer_time", "total_elapsed_time")),
                        "distance": _f(_v(frame, "total_distance")),
                        "ascent": _f(_v(frame, "total_ascent")),
                        "avg_hr": _f(_v(frame, "avg_heart_rate")),
                        "max_hr": _f(_v(frame, "max_heart_rate")),
                        "calories": _f(_v(frame, "total_calories")),
                        "cadence": _f(_v(frame, "avg_running_cadence", "avg_cadence")),
                    }
                elif frame.name == "record":
                    ts = _v(frame, "timestamp")
                    if isinstance(ts, datetime):
                        records.append(
                            (
                                _aware(ts),
                                {
                                    "hr": _f(_v(frame, "heart_rate")),
                                    "speed": _f(_v(frame, "enhanced_speed", "speed")),
                                    "altitude": _f(_v(frame, "enhanced_altitude", "altitude")),
                                    "cadence": _f(_v(frame, "cadence")),
                                    "power": _f(_v(frame, "power")),
                                    "distance": _f(_v(frame, "distance")),
                                },
                            )
                        )
                elif frame.name == "lap":
                    laps.append(
                        {
                            "start": _v(frame, "start_time"),
                            "duration": _f(_v(frame, "total_timer_time", "total_elapsed_time")),
                            "distance": _f(_v(frame, "total_distance")),
                            "avg_hr": _f(_v(frame, "avg_heart_rate")),
                            "max_hr": _f(_v(frame, "max_heart_rate")),
                        }
                    )
                elif frame.name == "set" and _v(frame, "set_type") in ("active", 1):
                    reps = _f(_v(frame, "repetitions"))
                    category = _v(frame, "category")
                    if isinstance(category, (list, tuple)):
                        category = category[0] if category else None
                    sets.append(
                        StrengthSet(
                            exercise=str(category) if category is not None else None,
                            reps=int(reps) if reps else None,
                            weight_kg=_f(_v(frame, "weight")),
                            duration_s=_f(_v(frame, "duration")),
                        )
                    )
    except fitdecode.FitError as exc:
        raise ActivityFileError(f"Archivo FIT inválido: {exc}") from exc

    start_raw = session.get("start") or (records[0][0] if records else None)
    if not isinstance(start_raw, datetime):
        raise ActivityFileError("El archivo FIT no contiene una actividad")
    start = _aware(start_raw)
    act = ParsedActivity(
        sport=str(session.get("sport") or "generic"),
        sub_sport=str(session["sub_sport"]) if session.get("sub_sport") else None,
        start=start,
        duration_s=_f(session.get("duration")) or 0.0,
        fingerprint=_hash("fit", file_id.get("serial"), file_id.get("created"), start.isoformat()),
        distance_m=_f(session.get("distance")),
        ascent_m=_f(session.get("ascent")),
        avg_hr=_f(session.get("avg_hr")),
        max_hr=_f(session.get("max_hr")),
        calories=_f(session.get("calories")),
        avg_cadence=_f(session.get("cadence")),
        samples=[Sample(t=(ts - start).total_seconds(), **vals) for ts, vals in records],
        laps=[_fit_lap(lap, start) for lap in laps],
        strength_sets=sets,
    )
    return _fill_summary(act)


# --- GPX / TCX ---------------------------------------------------------------------------


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(node: ET.Element, name: str) -> str | None:
    for child in node.iter():
        if _local(child.tag) == name and child.text and child.text.strip():
            return child.text.strip()
    return None


def _parse_time(text: str | None) -> datetime | None:
    if not text:
        return None
    try:
        return _aware(datetime.fromisoformat(text.replace("Z", "+00:00")))
    except ValueError:
        return None


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _xml(data: bytes) -> ET.Element:
    try:
        return ET.fromstring(data)
    except ET.ParseError as exc:
        raise ActivityFileError(f"XML inválido: {exc}") from exc


def _infer_sport(distance_m: float | None, duration_s: float) -> str:
    """GPX sin tipo: se deduce por la velocidad media (el usuario puede corregirlo)."""
    if not distance_m or duration_s <= 0:
        return "generic"
    speed = distance_m / duration_s
    return "walking" if speed < 2.0 else "running" if speed < 6.5 else "cycling"


def parse_gpx(data: bytes) -> ParsedActivity:
    root = _xml(data)
    points = [n for n in root.iter() if _local(n.tag) == "trkpt"]
    if not points:
        raise ActivityFileError("El GPX no contiene puntos de track")
    raw: list[tuple[datetime, float, float, dict[str, float | None]]] = []
    for pt in points:
        ts = _parse_time(_child_text(pt, "time"))
        if ts is None:
            continue
        raw.append(
            (
                ts,
                float(pt.get("lat", 0)),
                float(pt.get("lon", 0)),
                {
                    "altitude": _f(_child_text(pt, "ele")),
                    "hr": _f(_child_text(pt, "hr")),
                    "cadence": _f(_child_text(pt, "cad")),
                    "power": _f(_child_text(pt, "power")),
                },
            )
        )
    if not raw:
        raise ActivityFileError("El GPX no tiene tiempos")
    start = raw[0][0]
    distance = 0.0
    samples: list[Sample] = []
    for i, (ts, lat, lon, vals) in enumerate(raw):
        if i:
            distance += _haversine(raw[i - 1][1], raw[i - 1][2], lat, lon)
        samples.append(Sample(t=(ts - start).total_seconds(), distance=round(distance, 1), **vals))
    duration = samples[-1].t
    sport_text = (_child_text(root, "type") or "").lower()
    act = ParsedActivity(
        sport=sport_text or _infer_sport(distance, duration),
        sub_sport=None,
        start=start,
        duration_s=duration,
        fingerprint=_hash("gpx", start.isoformat(), round(distance)),
        samples=samples,
    )
    return _fill_summary(act)


TCX_SPORTS = {"running": "running", "biking": "cycling", "other": "generic"}


def parse_tcx(data: bytes) -> ParsedActivity:
    root = _xml(data)
    activity = next((n for n in root.iter() if _local(n.tag) == "Activity"), None)
    if activity is None:
        raise ActivityFileError("El TCX no contiene ninguna actividad")
    laps: list[Lap] = []
    samples: list[Sample] = []
    start: datetime | None = None
    calories = 0.0
    for lap in (n for n in activity if _local(n.tag) == "Lap"):
        lap_start = _parse_time(lap.get("StartTime"))
        start = start or lap_start
        calories += _f(_child_text(lap, "Calories")) or 0.0
        for tp in (n for n in lap.iter() if _local(n.tag) == "Trackpoint"):
            ts = _parse_time(_child_text(tp, "Time"))
            if ts is None or start is None:
                continue
            hr_node = next((n for n in tp if _local(n.tag) == "HeartRateBpm"), None)
            samples.append(
                Sample(
                    t=(ts - start).total_seconds(),
                    hr=_f(_child_text(hr_node, "Value")) if hr_node is not None else None,
                    altitude=_f(_child_text(tp, "AltitudeMeters")),
                    distance=_f(_child_text(tp, "DistanceMeters")),
                    cadence=_f(_child_text(tp, "Cadence")),
                    speed=_f(_child_text(tp, "Speed")),
                    power=_f(_child_text(tp, "Watts")),
                )
            )
        if lap_start is not None and start is not None:
            avg = next((n for n in lap if _local(n.tag) == "AverageHeartRateBpm"), None)
            mx = next((n for n in lap if _local(n.tag) == "MaximumHeartRateBpm"), None)
            laps.append(
                Lap(
                    start_s=(lap_start - start).total_seconds(),
                    duration_s=_f(_child_text(lap, "TotalTimeSeconds")) or 0.0,
                    distance_m=_f(_child_text(lap, "DistanceMeters")),
                    avg_hr=_f(_child_text(avg, "Value")) if avg is not None else None,
                    max_hr=_f(_child_text(mx, "Value")) if mx is not None else None,
                )
            )
    if start is None:
        raise ActivityFileError("El TCX no tiene vueltas con tiempo")
    act = ParsedActivity(
        sport=TCX_SPORTS.get((activity.get("Sport") or "other").lower(), "generic"),
        sub_sport=None,
        start=start,
        duration_s=sum(lap.duration_s for lap in laps),
        fingerprint=_hash("tcx", _child_text(activity, "Id") or start.isoformat()),
        calories=calories or None,
        samples=samples,
        laps=laps,
    )
    return _fill_summary(act)


def parse_activity(filename: str, data: bytes) -> ParsedActivity:
    name = filename.lower()
    if name.endswith(".fit") or data[8:12] == b".FIT":
        return parse_fit(data)
    if name.endswith(".gpx"):
        return parse_gpx(data)
    if name.endswith(".tcx"):
        return parse_tcx(data)
    raise ActivityFileError("Formato no soportado: usa .fit, .gpx o .tcx")


# --- Derivados ---------------------------------------------------------------------------


def km_splits(samples: list[Sample]) -> list[dict[str, float | None]]:
    """Parciales por km: tiempo, ritmo (s/km) y FC media de cada kilómetro."""
    points = [s for s in samples if s.distance is not None]
    splits: list[dict[str, float | None]] = []
    km, last_t, bucket = 1, 0.0, []
    for s in points:
        if s.hr:
            bucket.append(s.hr)
        if s.distance is not None and s.distance >= km * 1000:
            seconds = s.t - last_t
            splits.append(
                {
                    "km": km,
                    "seconds": round(seconds),
                    "paceSPerKm": round(seconds),
                    "avgHr": round(sum(bucket) / len(bucket)) if bucket else None,
                }
            )
            km, last_t, bucket = km + 1, s.t, []
    return splits


def downsample(samples: list[Sample], max_points: int = 1500) -> list[Sample]:
    if len(samples) <= max_points:
        return samples
    step = math.ceil(len(samples) / max_points)
    return samples[::step]
