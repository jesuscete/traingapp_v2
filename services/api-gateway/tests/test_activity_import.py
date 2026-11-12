from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient

from app.analytics.activity_file import ActivityFileError, parse_activity, parse_gpx, parse_tcx
from tests.fit_builder import running_fit, strength_fit

START = datetime(2026, 11, 10, 18, 0, tzinfo=UTC)


def _gpx(start: datetime, with_type: bool = True) -> bytes:
    points = []
    for i in range(0, 601, 10):  # 10 min a ~3 m/s hacia el norte (0,00027° ≈ 30 m)
        ts = (start + timedelta(seconds=i)).isoformat().replace("+00:00", "Z")
        points.append(
            f'<trkpt lat="{40 + i * 0.000027:.6f}" lon="-3.7"><ele>{650 + i // 60}</ele>'
            f"<time>{ts}</time><extensions><gpxtpx:TrackPointExtension>"
            f"<gpxtpx:hr>{140 + i // 60}</gpxtpx:hr></gpxtpx:TrackPointExtension>"
            "</extensions></trkpt>"
        )
    kind = "<type>running</type>" if with_type else ""
    return (
        '<?xml version="1.0"?><gpx xmlns="http://www.topografix.com/GPX/1/1" '
        'xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1">'
        f"<trk>{kind}<trkseg>{''.join(points)}</trkseg></trk></gpx>"
    ).encode()


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _tcx(start: datetime) -> bytes:
    iso = start.isoformat().replace("+00:00", "Z")
    tps = "".join(
        f"<Trackpoint><Time>{_iso(start + timedelta(seconds=s))}</Time>"
        f"<DistanceMeters>{s * 6}</DistanceMeters><HeartRateBpm><Value>130</Value></HeartRateBpm>"
        "</Trackpoint>"
        for s in range(0, 1201, 60)
    )
    return (
        '<?xml version="1.0"?><TrainingCenterDatabase '
        'xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"><Activities>'
        f'<Activity Sport="Biking"><Id>{iso}</Id><Lap StartTime="{iso}">'
        "<TotalTimeSeconds>1200</TotalTimeSeconds><DistanceMeters>7200</DistanceMeters>"
        f"<Calories>250</Calories><Track>{tps}</Track></Lap></Activity></Activities>"
        "</TrainingCenterDatabase>"
    ).encode()


def test_parsers_produce_a_common_activity() -> None:
    fit = parse_activity("carrera.fit", running_fit(START))
    assert (fit.sport, fit.distance_m, fit.avg_hr, fit.calories) == (
        "running",
        5400.0,
        150.0,
        400.0,
    )
    gpx = parse_gpx(_gpx(START))
    assert gpx.sport == "running" and 1700 < (gpx.distance_m or 0) < 1900
    assert gpx.max_hr == 150 and (gpx.ascent_m or 0) == 10
    untyped = parse_gpx(_gpx(START, with_type=False))
    assert untyped.sport == "running"  # deducido por la velocidad (~3 m/s)
    tcx = parse_tcx(_tcx(START))
    assert (tcx.sport, tcx.duration_s, tcx.calories, tcx.avg_hr) == ("cycling", 1200, 250, 130)
    with pytest.raises(ActivityFileError):
        parse_activity("notas.txt", b"hola")
    with pytest.raises(ActivityFileError):
        parse_activity("roto.gpx", b"<gpx>")


def _headers(client: TestClient, email: str) -> dict[str, str]:
    body = {"email": email, "password": "password123", "name": "R"}
    token = client.post("/auth/register", json=body).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.put(
        "/profile",
        json={"weightKg": 75, "heightCm": 178, "birthYear": 1994, "sex": "male", "maxHr": 191},
        headers=headers,
    )
    return headers


def _import(
    client: TestClient, headers: dict[str, str], name: str, data: bytes, **params: str
) -> httpx.Response:
    return client.post(
        "/activities/import", params={"filename": name, **params}, content=data, headers=headers
    )


def test_import_run_with_zones_trimp_and_dedup(client: TestClient) -> None:
    headers = _headers(client, "runner-import@example.com")
    start = datetime.now(UTC) - timedelta(hours=3)
    data = running_fit(start, minutes=40, hr=165)
    first = _import(client, headers, "carrera.fit", data)
    assert first.status_code == 200, first.text
    result = first.json()
    assert (result["status"], result["discipline"]) == ("imported", "running")
    assert result["suggestedMaxHr"] is None  # 175 < 191

    session = client.get(f"/sessions/{result['sessionId']}", headers=headers).json()
    assert session["distanceMeters"] == 7200 and session["estimatedKcal"] == 400
    assert session["details"]["metrics"]["kind"] == "endurance"
    detail = client.get(f"/activities/{result['sessionId']}", headers=headers).json()
    summary = detail["summary"]
    assert summary["hrProfile"]["maxHr"] == 191 and summary["hrProfile"]["restingEstimated"]
    assert summary["trimp"] > 50
    assert sum(summary["zonesSeconds"]) == pytest.approx(40 * 60, abs=10)
    assert len(summary["kmSplits"]) == 7
    assert len(detail["samples"]["hr"]) == len(detail["samples"]["t"]) > 400

    again = _import(client, headers, "carrera-copia.fit", data).json()
    assert again["status"] == "duplicate" and again["sessionId"] == result["sessionId"]

    fatigue = {
        m["muscleGroup"]: m["fatigue"]
        for m in client.get("/stats/fatigue", headers=headers).json()["muscles"]
    }
    assert fatigue["quadriceps"] > 0 and fatigue["calves"] > 0

    stranger = _headers(client, "stranger-import@example.com")
    assert client.get(f"/activities/{result['sessionId']}", headers=stranger).status_code == 404


def test_overlap_with_manual_session_and_force(client: TestClient) -> None:
    headers = _headers(client, "overlap@example.com")
    manual = {
        "discipline": "running",
        "rawText": "carrera",
        "durationMinutes": 30,
        "performedAt": START.isoformat(),
    }
    assert client.post("/sessions", json=manual, headers=headers).status_code == 201
    overlap = _import(client, headers, "carrera.fit", running_fit(START)).json()
    assert overlap["status"] == "overlap"
    forced = _import(client, headers, "carrera.fit", running_fit(START), force="true").json()
    assert forced["status"] == "imported"


def test_strength_fit_becomes_gym_session(client: TestClient) -> None:
    headers = _headers(client, "strength-import@example.com")
    result = _import(client, headers, "fuerza.fit", strength_fit(START)).json()
    assert (result["status"], result["discipline"]) == ("imported", "gym")
    session = client.get(f"/sessions/{result['sessionId']}", headers=headers).json()
    sets = session["workoutExercises"][0]["sets"]
    assert len(sets) == 3 and sets[0]["entries"][0]["reps"] == 8
    assert sets[0]["entries"][0]["weight"] == 60


def test_gpx_tcx_errors_and_max_hr_suggestion(client: TestClient) -> None:
    headers = _headers(client, "gpx-import@example.com")
    client.put("/profile", json={"maxHr": 145}, headers=headers)
    gpx = _import(client, headers, "salida.gpx", _gpx(START)).json()
    assert gpx["status"] == "imported" and gpx["suggestedMaxHr"] == 150
    tcx = _import(client, headers, "bici.tcx", _tcx(START + timedelta(days=1))).json()
    assert (tcx["status"], tcx["discipline"]) == ("imported", "cycling")
    bad = _import(client, headers, "nada.fit", b"no es un fit").json()
    assert bad["status"] == "error"
    assert _import(client, headers, "vacio.fit", b"").status_code == 422
    assert _import(client, headers, "x.doc", b"abc").json()["status"] == "error"
