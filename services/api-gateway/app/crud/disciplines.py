"""Loader del catalogo canonical de disciplinas para la capa analitica.

Convierte la tabla `discipline` (+ `discipline_muscle_load`) en un mapa en
memoria reutilizable por las analiticas (kcal, fatiga, impactos). Las funciones
puras aceptan catalogo explicito para no repetir consultas por llamada.
"""
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Discipline


@dataclass(frozen=True)
class DisciplineInfo:
    """Vista runtime de una disciplina del catalogo."""

    id: uuid.UUID
    code: str
    name: str
    met: float
    kind: str
    category: str
    muscle_load: dict[str, float] = field(default_factory=dict)

    @property
    def profile(self) -> dict[str, float]:
        """Perfil de impacto normalizado (0-1) para las analiticas de fatiga."""
        if not self.muscle_load:
            return {}
        max_load = max(self.muscle_load.values()) or 1.0
        return {
            group: round(load / max_load, 3)
            for group, load in self.muscle_load.items()
        }


@dataclass
class DisciplineCatalog:
    """Catalogo indexado por codigo canonical."""

    by_code: dict[str, DisciplineInfo] = field(default_factory=dict)

    @classmethod
    def build(cls, disciplines: list[Discipline]) -> "DisciplineCatalog":
        by_code: dict[str, DisciplineInfo] = {}
        for item in disciplines:
            by_code[item.normalized_name] = DisciplineInfo(
                id=item.id,
                code=item.normalized_name,
                name=item.name,
                met=item.met,
                kind=item.kind,
                category=item.category,
                muscle_load={
                    row.muscle_group: row.load for row in item.muscle_loads
                },
            )
        return cls(by_code=by_code)

    def info(self, code: str) -> DisciplineInfo | None:
        return self.by_code.get(code)

    @property
    def cardio_codes(self) -> frozenset[str]:
        return frozenset(
            code
            for code, info in self.by_code.items()
            if info.kind == "cardio"
        )


async def load_catalog(session: AsyncSession) -> DisciplineCatalog:
    result = await session.execute(
        select(Discipline).options(selectinload(Discipline.muscle_loads))
    )
    return DisciplineCatalog.build(list(result.scalars().all()))
