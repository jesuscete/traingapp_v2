"""Registro de conocimiento por deporte: carga, resolución y resumen compacto para la IA."""

from functools import lru_cache
from pathlib import Path

from app.analytics.catalog import normalize_exercise_name
from app.analytics.patterns import PATTERN_LABELS
from app.analytics.sport_analysis import GROUP_LABELS, SportProfile
from app.schemas.sport_profile import Goal, Phase, SportProfileDoc

PROFILES_DIR = Path(__file__).resolve().parents[2] / "data" / "sport_profiles"
DEFAULT_SPORT = "generic"


@lru_cache(maxsize=1)
def load_profiles() -> dict[str, SportProfileDoc]:
    """Perfiles validados indexados por deporte y por sus alias."""
    profiles: dict[str, SportProfileDoc] = {}
    for file in sorted(PROFILES_DIR.glob("*.json")):
        doc = SportProfileDoc.model_validate_json(file.read_text(encoding="utf-8"))
        for key in (doc.sport, *doc.aliases):
            profiles[key] = doc
    if DEFAULT_SPORT not in profiles:
        raise RuntimeError(f"Falta el perfil por defecto '{DEFAULT_SPORT}' en {PROFILES_DIR}")
    return profiles


def profile_doc(sport: str | None) -> SportProfileDoc:
    profiles = load_profiles()
    return profiles.get(sport or "", profiles[DEFAULT_SPORT])


def sport_profile(sport: str | None, phase: Phase = "general") -> SportProfile:
    """Perfil listo para el analizador (las zonas de reps dependen de la fase)."""
    doc = profile_doc(sport)
    zones = doc.rep_zones_by_phase.get(phase) or doc.rep_zones_by_phase["general"]
    return SportProfile(
        sport=doc.sport,
        label=doc.label,
        pattern_targets=doc.pattern_targets,
        muscle_targets=doc.muscle_targets,
        rep_zones={str(zone): bounds for zone, bounds in zones.items()},
        min_pull_push_ratio=doc.min_pull_push_ratio,
        conflict_groups=frozenset(doc.conflict_groups),
    )


def block_weights(sport: str, block_type: str) -> dict[str, float] | None:
    """Pesos musculares de un tipo de bloque (p. ej. comba), si el deporte los define."""
    doc = load_profiles().get(sport)
    return doc.block_muscle_weights.get(block_type) if doc else None


def compact_summary(sport: str | None, phase: Phase = "general") -> str:
    """Resumen breve (~300 tokens) para incluir en prompts en lugar de que la IA lo deduzca."""
    doc = profile_doc(sport)
    qualities = ", ".join(q.label for q in sorted(doc.qualities, key=lambda q: -q.priority))
    patterns = "; ".join(
        f"{PATTERN_LABELS[p]} ≥{t:g}"
        + (f" ({', '.join(doc.key_exercises[p][:2])})" if doc.key_exercises.get(p) else "")
        for p, t in doc.pattern_targets.items()
    )
    muscles = ", ".join(
        f"{GROUP_LABELS.get(g, g)} {lo:g}-{hi:g}" for g, (lo, hi) in doc.muscle_targets.items()
    )
    zones = doc.rep_zones_by_phase.get(phase) or doc.rep_zones_by_phase["general"]
    zones_text = ", ".join(f"{z} {lo:.0%}-{hi:.0%}" for z, (lo, hi) in zones.items())
    lines = [
        f"PERFIL DE {doc.label.upper()} (v{doc.version}, fase {phase}): {doc.summary}",
        f"Cualidades por prioridad: {qualities}.",
        f"Patrones (series/semana): {patterns}.",
        f"Series/semana por músculo: {muscles}.",
        f"Zonas de repeticiones: {zones_text}.",
    ]
    if doc.load_rules:
        lines.append("Reglas: " + " ".join(doc.load_rules))
    if doc.injury_risks:
        lines.append(
            "Prevención: "
            + "; ".join(f"{r.zona}: {', '.join(r.prehab[:2])}" for r in doc.injury_risks)
            + "."
        )
    if doc.coach_notes:
        lines.append(f"Notas: {doc.coach_notes}")
    return "\n".join(lines)


_MARTIAL_KEYS = frozenset({"martial_arts", "kickboxing", "muay thai", "mma", "artes marciales"})


def resolve_sport(raw: str | None) -> str | None:
    """Nombre libre de deporte («boxeo», «correr») -> clave de perfil, o None si no hay perfil.

    Una sola tabla de alias: la de los propios perfiles (`aliases`), normalizada.
    """
    if not raw:
        return None
    key = normalize_exercise_name(raw)
    doc = _normalized_index().get(key)
    if doc is None or doc.sport == DEFAULT_SPORT:
        return None
    return "martial_arts" if key in _MARTIAL_KEYS else doc.sport


@lru_cache(maxsize=1)
def _normalized_index() -> dict[str, SportProfileDoc]:
    return {normalize_exercise_name(k): doc for k, doc in load_profiles().items()}


def find_goal(sport: str | None, text: str) -> Goal | None:
    """Objetivo del perfil cuyo sinónimo aparece en el texto (el más largo gana)."""
    folded = f" {normalize_exercise_name(text)} "
    best: tuple[int, Goal] | None = None
    for goal in profile_doc(sport).goals:
        for synonym in goal.synonyms:
            needle = normalize_exercise_name(synonym)
            if needle and f" {needle} " in folded and (best is None or len(needle) > best[0]):
                best = (len(needle), goal)
    return best[1] if best else None


def goal_patterns(sport: str | None, goal: Goal) -> list[tuple[str, int]]:
    """Patrones que desarrolla un objetivo, con la prioridad de su cualidad (mayor primero)."""
    doc = profile_doc(sport)
    priority: dict[str, int] = {}
    for quality in doc.qualities:
        if quality.key in goal.qualities:
            for pattern in quality.patterns:
                priority[pattern] = max(priority.get(pattern, 0), quality.priority)
    return sorted(priority.items(), key=lambda kv: (-kv[1], kv[0]))
