"""Fallback determinista para la generacion de planes (sin LLM).

Contrato identico al del LLM (mismo JSON). Los ejercicios se eligen SOLO del
catalogo recibido, por coincidencia de palabras clave con el grupo muscular.
"""

import re
import unicodedata

from app.schemas.plan import (
    PlanDay,
    PlanExercise,
    PlanResponse,
    PlanSetTarget,
    SplitOption,
    SplitResponse,
    SportIn,
)

_MUSCLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "chest": (
        "press banca",
        "press inclinado",
        "press declinado",
        "aperturas",
        "press con mancuernas",
    ),
    "back": (
        "peso muerto",
        "dominadas",
        "jalon al pecho",
        "remo con barra",
        "remo mancuerna",
        "remo sentado",
    ),
    "shoulders": (
        "press militar",
        "elevaciones laterales",
        "elevaciones frontales",
        "elevaciones posteriores",
        "face pull",
    ),
    "legs": (
        "sentadilla",
        "sentadilla frontal",
        "prensa",
        "zancadas",
        "extension de cuadriceps",
        "curl femoral",
        "peso muerto rumano",
        "hip thrust",
        "gemelos",
        "elevacion de talones",
    ),
    "arms": (
        "curl biceps",
        "curl martillo",
        "press frances",
        "push down",
        "extensiones de triceps",
        "fondos en paralelas",
    ),
    "core": ("plancha", "crunches", "russian twist", "elevacion de piernas"),
}

# Ejercicios de potencia/explosividad (rendimiento deportivo). Se priorizan en
# los dias de gimnasio cuando el objetivo es performance y hay deporte.
_EXPLOSIVE_KEYWORDS: tuple[str, ...] = (
    "press empujadora",
    "landmine press",
    "cargada de potencia",
    "balanceo con kettlebell",
    "saltos al cajon",
    "saltos verticales",
    "lanzamiento de balon medicinal",
)

# Clasificacion muscular extra para los ejercicios explosivos del catalogo
# (subcadenas sobre el nombre normalizado).
_EXPLOSIVE_MUSCLES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("press empujadora", ("shoulders", "triceps", "chest")),
    ("landmine press", ("shoulders", "core", "triceps", "chest")),
    ("cargada de potencia", ("back", "legs", "shoulders", "core")),
    ("balanceo con kettlebell", ("legs", "back", "core")),
    ("saltos al cajon", ("legs", "core")),
    ("saltos verticales", ("legs", "core")),
    ("lanzamiento de balon medicinal", ("core", "shoulders", "chest")),
)

# (id, name, [muscle groups por dia de gym])
_SPLIT_TEMPLATES: dict[str, tuple[str, tuple[tuple[str, ...], ...]]] = {
    "fullbody_1": ("Fullbody 1 día", (("legs", "chest", "back", "shoulders", "core"),)),
    "fullbody_2": (
        "Fullbody 2 días",
        (
            ("legs", "chest", "back", "shoulders"),
            ("legs", "chest", "back", "arms", "core"),
        ),
    ),
    "fullbody_3": (
        "Fullbody 3 días",
        (
            ("legs", "chest", "back", "core"),
            ("legs", "chest", "back", "shoulders"),
            ("legs", "back", "arms", "core"),
        ),
    ),
    "upper_lower_fullbody": (
        "Torso / Pierna + Fullbody",
        (
            ("chest", "back", "shoulders", "arms", "core"),
            ("legs", "core"),
            ("legs", "chest", "back", "core"),
        ),
    ),
    "push_pull_legs": (
        "Push / Pull / Pierna",
        (
            ("chest", "shoulders", "arms"),
            ("back", "arms", "core"),
            ("legs", "core"),
        ),
    ),
    "torso_pierna": (
        "Torso / Pierna (2 días)",
        (
            ("chest", "back", "shoulders", "arms", "core"),
            ("legs", "core"),
        ),
    ),
    "torso_pierna_2x": (
        "Torso / Pierna x2 (frecuencia 2)",
        (
            ("chest", "back", "shoulders", "core"),
            ("legs", "core"),
            ("chest", "back", "arms", "core"),
            ("legs", "core"),
        ),
    ),
    "fullbody_4": (
        "Fullbody 4 días",
        (
            ("legs", "chest", "back", "core"),
            ("legs", "chest", "back", "shoulders", "core"),
            ("legs", "back", "arms", "core"),
            ("legs", "chest", "shoulders", "arms", "core"),
        ),
    ),
    "upper_lower_3x": (
        "Torso / Pierna frecuencia 3",
        (
            ("chest", "back", "shoulders", "core"),
            ("legs", "core"),
            ("chest", "back", "arms", "core"),
            ("legs", "core"),
            ("legs", "chest", "back", "core"),
        ),
    ),
    "push_pull_legs_2x": (
        "Push / Pull / Pierna x2",
        (
            ("chest", "shoulders", "arms", "core"),
            ("back", "arms", "core"),
            ("legs", "core"),
            ("chest", "shoulders", "arms", "core"),
            ("back", "arms", "core"),
            ("legs", "core"),
        ),
    ),
}

# Objetivo -> protocolo (series, reps min, max, descanso s) para ejercicios
# principales (grupos del split) y de apoyo (refuerzo al deporte).
_MAIN_PROTOCOL: dict[str, tuple[int, int, int, int]] = {
    "aesthetic": (3, 10, 15, 90),
    "performance": (3, 6, 10, 120),
}
_SUPPORT_PROTOCOL: dict[str, tuple[int, int, int, int]] = {
    "aesthetic": (3, 12, 15, 60),
    "performance": (3, 10, 15, 60),
}

# Protocolo para ejercicios de potencia/explosividad (series, reps min, max, descanso s).
_POWER_PROTOCOL: dict[str, tuple[int, int, int, int]] = {
    "aesthetic": (3, 6, 10, 90),
    "performance": (3, 3, 6, 120),
}

# Palabras clave del deporte -> grupos de apoyo.
_SPORT_SUPPORT: dict[str, tuple[str, ...]] = {
    "boxing": ("core", "shoulders"),
    "martial_arts": ("core", "shoulders"),
    "running": ("legs", "core"),
    "cycling": ("legs", "core"),
    "swimming": ("back", "shoulders", "core"),
    "climbing": ("back", "arms", "core"),
    "football": ("legs", "core", "shoulders"),
    "basketball": ("legs", "core", "shoulders"),
    "volleyball": ("legs", "shoulders", "core"),
    "tennis": ("legs", "core", "shoulders"),
    "calisthenics": ("core", "back"),
}
_DEFAULT_SUPPORT: tuple[str, ...] = ("core", "legs")

# Nombres en español (forma display del chat) -> clave de _SPORT_SUPPORT.
_SPORT_ALIASES: dict[str, str] = {
    "boxeo": "boxing",
    "correr": "running",
    "corro": "running",
    "carrera": "running",
    "trote": "running",
    "jogging": "running",
    "bicicleta": "cycling",
    "bici": "cycling",
    "ciclismo": "cycling",
    "natacion": "swimming",
    "escalada": "climbing",
    "futbol": "football",
    "baloncesto": "basketball",
    "voleibol": "volleyball",
    "voley": "volleyball",
    "tenis": "tennis",
    "calistenia": "calisthenics",
    "artes marciales": "martial_arts",
}


def normalize_name(name: str) -> str:
    lowered = name.lower().strip()
    no_accents = "".join(
        char
        for char in unicodedata.normalize("NFD", lowered)
        if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"[^a-z0-9 ]+", " ", no_accents).strip()


def _muscle_groups(name: str) -> set[str]:
    normalized = normalize_name(name)
    groups: set[str] = set()
    for group, keywords in _MUSCLE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized:
                groups.add(group)
    for keyword, extra in _EXPLOSIVE_MUSCLES:
        if keyword in normalized:
            groups.update(extra)
    return groups


def _is_explosive(name: str) -> bool:
    normalized = normalize_name(name)
    return any(keyword in normalized for keyword in _EXPLOSIVE_KEYWORDS)


def _occupied_days(sports: list[SportIn]) -> set[int]:
    days: set[int] = set()
    for sport in sports:
        days.update(sport.days)
    return days


def _sport_key(name: str) -> str:
    normalized = normalize_name(name)
    if normalized in _SPORT_ALIASES:
        return _SPORT_ALIASES[normalized]
    for key in _SPORT_SUPPORT:
        if key in normalized or normalized in _SPORT_SUPPORT:
            return key
    return "other"


def _sport_discipline(name: str) -> str:
    """Normalized del deporte declarado (se ajusta en el gateway al catalogo)."""
    return normalize_name(name)


def _build_catalog_index(
    catalog: list[str],
) -> tuple[dict[str, tuple[str, set[str]]], dict[str, str]]:
    index: dict[str, tuple[str, set[str]]] = {}
    by_display: dict[str, str] = {}
    for display in catalog:
        norm = normalize_name(display)
        if not norm:
            continue
        if norm not in index:
            index[norm] = (display, _muscle_groups(display))
            by_display[display] = norm
    return index, by_display


def _pick_exercises(
    index: dict[str, tuple[str, set[str]]],
    groups: tuple[str, ...],
    needed: int,
    offset: int = 0,
    exclude: set[str] | None = None,
) -> list[str]:
    """Toma hasta `needed` ejercicios del catalogo que cubran los grupos dados.

    - `offset`: rotacion sobre el orden del catalogo para variar entre dias.
    - `exclude`: nombres normalizados a evitar; si no hay suficientes sin excluir,
      se reciclan los excluidos para no dejar el dia incompleto.
    Los ejercicios de potencia/explosividad se omiten aqui: solo se incluyen de
    forma explicita en dias de gimnasio con perfil de rendimiento deportivo.
    """
    items = list(index.items())
    if not items:
        return []
    n = len(items)
    ordered = [items[(i + offset) % n] for i in range(n)]

    def matches(norm: str, display: str, muscle_groups: set[str]) -> bool:
        if _is_explosive(display):
            return False
        if exclude and norm in exclude:
            return False
        return any(group in muscle_groups for group in groups)

    fresh = [
        display
        for norm, (display, muscle_groups) in ordered
        if matches(norm, display, muscle_groups)
    ]
    if len(fresh) < needed and exclude:
        recycled = [
            display
            for norm, (display, muscle_groups) in ordered
            if norm in exclude and not _is_explosive(display)
            and any(group in muscle_groups for group in groups)
        ]
        fresh = fresh + recycled
    return fresh[:needed]


def suggest_splits_stub(
    sports: list[SportIn], gym_days: int
) -> SplitResponse:
    if gym_days <= 0:
        return SplitResponse(options=[])
    occupied = _occupied_days(sports)
    free = 7 - len(occupied)
    options: list[SplitOption] = []
    if free <= 0:
        return SplitResponse(options=[])
    if gym_days == 1:
        ids = ["fullbody_1"]
    elif gym_days == 2:
        ids = ["fullbody_2", "torso_pierna"]
    elif gym_days == 3:
        ids = ["push_pull_legs", "upper_lower_fullbody", "fullbody_3"]
    elif gym_days == 4:
        ids = ["torso_pierna_2x", "fullbody_4"]
    elif gym_days == 5:
        ids = ["upper_lower_3x", "push_pull_legs_2x"]
    else:
        ids = ["push_pull_legs_2x"]
    for split_id in ids:
        name, _ = _SPLIT_TEMPLATES[split_id]
        description = (
            f"{name}. Entrena {gym_days} días de gimnasio en tus días libres "
            f"({free} disponibles). "
        )
        if sports:
            description += (
                "Se evita cargar pierna el día antes de tus sesiones de deporte "
                "para no condicionar el rendimiento."
            )
        else:
            description += "Distribución equilibrada de la carga semanal."
        options.append(
            SplitOption(
                id=split_id,
                name=name,
                description=description,
            )
        )
    return SplitResponse(options=options[:3])


def _assign_gym_days(
    occupied: set[int], template: tuple[tuple[str, ...], ...]
) -> list[tuple[int, tuple[str, ...]]]:
    """Asigna los slots del template a dias libres (1=lunes ... 7=domingo).

    Heuristica: los dias de pierna se desplazan de un dia inmediatamente
    anterior a un deporte si hay otro dia libre disponible despues.
    """
    free = sorted(day for day in range(1, 8) if day not in occupied)
    slots = list(template)
    if not free:
        return []
    assignments: list[tuple[int, tuple[str, ...]]] = []
    used: set[int] = set()
    for slot in slots:
        candidate = next((day for day in free if day not in used), None)
        if candidate is None:
            break
        is_legs = "legs" in slot
        if is_legs and (candidate % 7) + 1 in occupied:
            alternative = next(
                (day for day in free if day not in used and day != candidate), None
            )
            if alternative is not None:
                candidate = alternative
        used.add(candidate)
        assignments.append((candidate, slot))
    return assignments


def _support_for(sports: list[SportIn], goal: str) -> list[str]:
    if goal != "performance" or not sports:
        return []
    groups: list[str] = []
    seen: set[str] = set()
    for sport in sports:
        for group in _SPORT_SUPPORT.get(_sport_key(sport.name), _DEFAULT_SUPPORT):
            if group not in seen:
                groups.append(group)
                seen.add(group)
    return groups


def _sets_for(
    protocol: tuple[int, int, int, int],
) -> list[PlanSetTarget]:
    series, reps_min, reps_max, rest = protocol
    return [
        PlanSetTarget(
            target_reps_min=reps_min,
            target_reps_max=reps_max,
            target_rest_seconds=rest,
        )
        for _ in range(series)
    ]


def generate_plan_stub(
    sports: list[SportIn],
    gym_days: int,
    split_id: str | None,
    goal: str,
    catalog: list[str],
) -> PlanResponse:
    index, _ = _build_catalog_index(catalog)
    explosive = [
        display
        for _norm, (display, _muscle_groups) in index.items()
        if _is_explosive(display)
    ]
    occupied = _occupied_days(sports)
    free_days = [day for day in range(1, 8) if day not in occupied]
    gym_days = min(gym_days, len(free_days))

    template = _SPLIT_TEMPLATES.get(split_id or "", ("Fullbody", ((*_DEFAULT_SUPPORT,),)))
    template_slots = template[1]
    if len(template_slots) > gym_days:
        template_slots = template_slots[:gym_days]
    while len(template_slots) < gym_days:
        template_slots = template_slots + ((*_DEFAULT_SUPPORT,),)

    assignments = _assign_gym_days(occupied, template_slots)
    support = _support_for(sports, goal)
    add_power = goal == "performance" and bool(sports) and bool(explosive)
    main_protocol = _MAIN_PROTOCOL.get(goal, _MAIN_PROTOCOL["aesthetic"])
    support_protocol = _SUPPORT_PROTOCOL.get(goal, _SUPPORT_PROTOCOL["aesthetic"])
    power_protocol = _POWER_PROTOCOL.get(goal, _POWER_PROTOCOL["aesthetic"])

    days: list[PlanDay] = []
    gym_slot_index = 0
    used_main: set[str] = set()
    used_support: set[str] = set()
    for day_of_week in range(1, 8):
        if day_of_week in occupied:
            sport = next(
                (item for item in sports if day_of_week in item.days),
                sports[0] if sports else None,
            )
            if sport is None:
                continue
            days.append(
                PlanDay(
                    day_of_week=day_of_week,
                    day_type="deporte",
                    label=sport.name,
                    discipline=_sport_discipline(sport.name),
                    duration_min=sport.duration_min,
                )
            )
            continue
        gym_day = next(
            (assign for assign in assignments if assign[0] == day_of_week), None
        )
        if gym_day is not None:
            groups = gym_day[1]

            power_picks: list[str] = []
            if add_power:
                for i in range(min(2, len(explosive))):
                    pick = explosive[(gym_slot_index * 2 + i) % len(explosive)]
                    if normalize_name(pick) not in {
                        normalize_name(p) for p in power_picks
                    }:
                        power_picks.append(pick)

            main_needed = 3 if add_power else 4
            support_needed = 1 if add_power else 2
            main_picks = _pick_exercises(
                index,
                groups,
                main_needed,
                offset=gym_slot_index * 3,
                exclude=used_main,
            )
            used_main.update(normalize_name(name) for name in main_picks)

            exercises = [
                PlanExercise(name=name, sets=_sets_for(main_protocol))
                for name in main_picks
            ]
            if support:
                support_picks = _pick_exercises(
                    index,
                    tuple(support),
                    support_needed,
                    offset=gym_slot_index,
                    exclude=used_support | used_main,
                )
                used_support.update(
                    normalize_name(name) for name in support_picks
                )
                exercises.extend(
                    PlanExercise(name=name, sets=_sets_for(support_protocol))
                    for name in support_picks
                )
            if power_picks:
                exercises = [
                    PlanExercise(name=name, sets=_sets_for(power_protocol))
                    for name in power_picks
                ] + exercises
            # Red de seguridad: sin duplicados dentro del mismo dia.
            seen: set[str] = set()
            unique_exercises: list[PlanExercise] = []
            for exercise in exercises:
                key = normalize_name(exercise.name)
                if key in seen:
                    continue
                seen.add(key)
                unique_exercises.append(exercise)
            exercises = unique_exercises
            gym_slot_index += 1
            days.append(
                PlanDay(
                    day_of_week=day_of_week,
                    day_type="gimnasio",
                    label=f"Gimnasio {len([d for d in days if d.day_type == 'gimnasio']) + 1}",
                    exercises=exercises,
                )
            )
            continue
        days.append(
            PlanDay(
                day_of_week=day_of_week,
                day_type="descanso",
                label="Descanso",
            )
        )

    template_name = _SPLIT_TEMPLATES.get(split_id or "", ("Fullbody", ()))[0]
    sports_name = " + ".join(sport.name for sport in sports)
    if split_id is None:
        name = sports_name or "Fullbody"
    elif sports_name:
        name = f"{template_name} - {sports_name}"
    else:
        name = template_name
    return PlanResponse(
        name=name,
        days=days,
    )
