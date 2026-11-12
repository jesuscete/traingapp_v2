"""Generador mínimo de archivos FIT para tests (especificación FIT: cabecera, definiciones,
datos y CRC). Solo los mensajes que usa el importador: file_id, record, lap, session, set."""

import struct
from datetime import UTC, datetime

FIT_EPOCH = datetime(1989, 12, 31, tzinfo=UTC)
CRC_TABLE = (
    0x0000,
    0xCC01,
    0xD801,
    0x1400,
    0xF001,
    0x3C00,
    0x2800,
    0xE401,
    0xA001,
    0x6C00,
    0x7800,
    0xB401,
    0x5000,
    0x9C01,
    0x8801,
    0x4400,
)

# (número de campo, formato struct, tipo base FIT)
U8, U16, U32, U32Z = ("B", 0x02), ("H", 0x84), ("I", 0x86), ("I", 0x8C)
ENUM = ("B", 0x00)

MESSAGES: dict[str, tuple[int, list[tuple[str, int, tuple[str, int]]]]] = {
    "file_id": (
        0,
        [("type", 0, ENUM), ("manufacturer", 1, U16), ("serial", 3, U32Z), ("created", 4, U32)],
    ),
    "record": (
        20,
        [
            ("timestamp", 253, U32),
            ("altitude", 2, U16),
            ("hr", 3, U8),
            ("cadence", 4, U8),
            ("distance", 5, U32),
            ("speed", 6, U16),
        ],
    ),
    "lap": (
        19,
        [
            ("timestamp", 253, U32),
            ("start", 2, U32),
            ("elapsed", 7, U32),
            ("timer", 8, U32),
            ("distance", 9, U32),
            ("avg_hr", 15, U8),
            ("max_hr", 16, U8),
        ],
    ),
    "session": (
        18,
        [
            ("timestamp", 253, U32),
            ("start", 2, U32),
            ("sport", 5, ENUM),
            ("sub_sport", 6, ENUM),
            ("elapsed", 7, U32),
            ("timer", 8, U32),
            ("distance", 9, U32),
            ("calories", 11, U16),
            ("avg_hr", 16, U8),
            ("max_hr", 17, U8),
            ("ascent", 22, U16),
        ],
    ),
    "set": (
        225,
        [
            ("timestamp", 254, U32),
            ("duration", 0, U32),
            ("reps", 3, U16),
            ("weight", 4, U16),
            ("set_type", 5, U8),
            ("start", 6, U32),
        ],
    ),
}
SPORT = {"running": 1, "cycling": 2, "swimming": 5, "training": 10}
SUB_SPORT = {"generic": 0, "strength_training": 20}


def _crc(data: bytes, crc: int = 0) -> int:
    for byte in data:
        tmp = CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc ^= tmp ^ CRC_TABLE[byte & 0xF]
        tmp = CRC_TABLE[crc & 0xF]
        crc = (crc >> 4) & 0x0FFF
        crc ^= tmp ^ CRC_TABLE[(byte >> 4) & 0xF]
    return crc


def fit_ts(dt: datetime) -> int:
    return int((dt - FIT_EPOCH).total_seconds())


class FitBuilder:
    def __init__(self) -> None:
        self._body = bytearray()
        self._local: dict[str, int] = {}

    def add(self, message: str, **values: int) -> "FitBuilder":
        global_num, fields = MESSAGES[message]
        if message not in self._local:
            local = len(self._local)
            self._local[message] = local
            definition = struct.pack("<BBBHB", 0x40 | local, 0, 0, global_num, len(fields))
            for _, num, (fmt, base) in fields:
                definition += struct.pack("<BBB", num, struct.calcsize(fmt), base)
            self._body += definition
        local = self._local[message]
        data = struct.pack("<B", local)
        for name, _, (fmt, _) in fields:
            invalid = {"B": 0xFF, "H": 0xFFFF, "I": 0xFFFFFFFF}[fmt]
            data += struct.pack("<" + fmt, values.get(name, invalid))
        self._body += data
        return self

    def build(self) -> bytes:
        header = struct.pack("<BBHI4s", 14, 0x20, 2132, len(self._body), b".FIT")
        header += struct.pack("<H", _crc(header))
        content = header + bytes(self._body)
        return content + struct.pack("<H", _crc(content))


def running_fit(start: datetime, minutes: int = 30, hr: int = 150, serial: int = 12345) -> bytes:
    """Carrera a 3 m/s (~5:33/km) con una muestra cada 5 s y FC constante."""
    b = FitBuilder().add("file_id", type=4, manufacturer=1, serial=serial, created=fit_ts(start))
    seconds = minutes * 60
    for t in range(0, seconds + 1, 5):
        b.add(
            "record",
            timestamp=fit_ts(start) + t,
            hr=hr,
            distance=t * 3 * 100,
            speed=3000,
            altitude=(100 + t // 60 + 500) * 5,
            cadence=85,
        )
    b.add(
        "lap",
        timestamp=fit_ts(start) + seconds,
        start=fit_ts(start),
        elapsed=seconds * 1000,
        timer=seconds * 1000,
        distance=seconds * 3 * 100,
        avg_hr=hr,
        max_hr=hr + 10,
    )
    b.add(
        "session",
        timestamp=fit_ts(start) + seconds,
        start=fit_ts(start),
        sport=SPORT["running"],
        sub_sport=0,
        elapsed=seconds * 1000,
        timer=seconds * 1000,
        distance=seconds * 3 * 100,
        calories=400,
        avg_hr=hr,
        max_hr=hr + 10,
        ascent=minutes,
    )
    return b.build()


def strength_fit(start: datetime) -> bytes:
    """Sesión de fuerza de Garmin: 3 series activas (8 reps x 60 kg) con descansos."""
    b = FitBuilder().add("file_id", type=4, manufacturer=1, serial=999, created=fit_ts(start))
    t = fit_ts(start)
    for i in range(3):
        b.add("set", timestamp=t + 60, start=t, duration=40_000, reps=8, weight=60 * 16, set_type=1)
        b.add("set", timestamp=t + 150, start=t + 60, duration=90_000, set_type=0)
        t += 150
    b.add(
        "session",
        timestamp=t,
        start=fit_ts(start),
        sport=SPORT["training"],
        sub_sport=SUB_SPORT["strength_training"],
        elapsed=450_000,
        timer=450_000,
        calories=120,
        avg_hr=110,
        max_hr=140,
    )
    return b.build()
