import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class ImportResultOut(CamelModel):
    filename: str
    status: Literal["imported", "duplicate", "overlap", "error"]
    message: str
    session_id: uuid.UUID | None = None
    discipline: str | None = None
    # Si la actividad supera tu FC máxima guardada (o estimada), se propone actualizarla.
    suggested_max_hr: int | None = None


class ActivityDetailOut(CamelModel):
    session_id: uuid.UUID
    discipline: str
    summary: dict[str, object] | None  # zonas, TRIMP, parciales, perfil de FC…
    samples: dict[str, list[float | None]]  # arrays alineados: t, hr, speed, altitude…
    laps: list[dict[str, object]]
