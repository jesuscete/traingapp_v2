"""Esquema del registro de conocimiento por deporte (`data/sport_profiles/*.json`).

Una sola fuente estructurada por deporte que consumen el analizador (M4), la fatiga
(pesos por tipo de bloque) y la IA (resumen compacto y herramienta `perfil_deporte`).
"""

from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.analytics.fatigue import MUSCLE_GROUPS
from app.analytics.patterns import PATTERN_LABELS
from app.schemas.metrics import CombatBlockType

RepZone = Literal["fuerza", "hipertrofia", "resistencia"]
Phase = Literal["general", "especifica", "precompeticion", "descarga"]
COMBAT_BLOCKS: frozenset[str] = frozenset(get_args(CombatBlockType))


def _check_groups(groups: set[str]) -> None:
    unknown = groups - set(MUSCLE_GROUPS)
    if unknown:
        raise ValueError(f"Grupos musculares desconocidos: {sorted(unknown)}")


def _check_weights(weights: dict[str, float]) -> dict[str, float]:
    _check_groups(set(weights))
    if any(not 0 <= w <= 1 for w in weights.values()):
        raise ValueError("Los pesos musculares deben estar entre 0 y 1")
    return weights


class Quality(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str
    label: str
    priority: int = Field(ge=1, le=5)


class InjuryRisk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    zona: str
    riesgo: str
    prehab: list[str] = Field(default_factory=list)


class SportProfileDoc(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sport: str
    label: str
    aliases: list[str] = Field(default_factory=list)
    version: int = Field(ge=1)
    summary: str
    qualities: list[Quality]
    energy_systems: dict[str, str] = Field(default_factory=dict)
    pattern_targets: dict[str, float]
    key_exercises: dict[str, list[str]] = Field(default_factory=dict)
    muscle_targets: dict[str, tuple[float, float]]
    rep_zones_by_phase: dict[Phase, dict[RepZone, tuple[float, float]]]
    min_pull_push_ratio: float = Field(gt=0)
    conflict_groups: list[str] = Field(default_factory=list)
    load_rules: list[str] = Field(default_factory=list)
    injury_risks: list[InjuryRisk] = Field(default_factory=list)
    block_muscle_weights: dict[str, dict[str, float]] = Field(default_factory=dict)
    coach_notes: str = ""

    @field_validator("pattern_targets", "key_exercises")
    @classmethod
    def _known_patterns(cls, value: dict[str, object]) -> dict[str, object]:
        unknown = set(value) - set(PATTERN_LABELS)
        if unknown:
            raise ValueError(f"Patrones desconocidos: {sorted(unknown)}")
        return value

    @field_validator("muscle_targets")
    @classmethod
    def _valid_ranges(cls, value: dict[str, tuple[float, float]]) -> dict[str, tuple[float, float]]:
        _check_groups(set(value))
        if any(low > high for low, high in value.values()):
            raise ValueError("Rango de series inválido (mínimo > máximo)")
        return value

    @field_validator("conflict_groups")
    @classmethod
    def _valid_conflicts(cls, value: list[str]) -> list[str]:
        _check_groups(set(value))
        return value

    @field_validator("block_muscle_weights")
    @classmethod
    def _valid_blocks(cls, value: dict[str, dict[str, float]]) -> dict[str, dict[str, float]]:
        unknown = set(value) - COMBAT_BLOCKS
        if unknown:
            raise ValueError(f"Tipos de bloque desconocidos: {sorted(unknown)}")
        return {block: _check_weights(weights) for block, weights in value.items()}

    @model_validator(mode="after")
    def _has_general_phase(self) -> "SportProfileDoc":
        if "general" not in self.rep_zones_by_phase:
            raise ValueError("rep_zones_by_phase necesita la fase 'general'")
        return self
