import re
import unicodedata

_MUSCLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "chest": (
        "press banca",
        "press inclinado",
        "press declinado",
        "aperturas",
        "fondos en paralelas",
        "cruces en polea",
        "press con mancuernas",
    ),
    "back": (
        "peso muerto",
        "dominadas",
        "jalon",
        "remo",
        "remo con barra",
        "remo mancuerna",
        "remo sentado",
        "pull over",
        "face pull",
    ),
    "shoulders": (
        "press militar",
        "press de hombro",
        "elevaciones laterales",
        "elevaciones frontales",
        "elevaciones posteriores",
        "pajarito",
        "vuelos laterales",
        "face pull",
    ),
    "legs": (
        "sentadilla",
        "sentadilla frontal",
        "prensa",
        "zancadas",
        "extensiones de cuadriceps",
        "curl femoral",
        "peso muerto rumano",
        "hip thrust",
        "gemelos",
        "elevacion de talones",
        "gluteos",
        "abduccion",
        "adduccion",
        "patada",
    ),
    "arms": (
        "curl biceps",
        "curl de biceps",
        "curl martillo",
        "curl araña",
        "press frances",
        "extensiones de triceps",
        "fondo triceps",
        "push down",
        "polea triceps",
        "copa",
    ),
    "core": (
        "plancha",
        "crunches",
        "abdominales",
        "russian twist",
        "mountain climber",
        "elevacion de piernas",
        "sit up",
        "hollow",
    ),
}


def _normalize(name: str) -> str:
    lowered = name.lower().strip()
    no_accents = "".join(
        char for char in unicodedata.normalize("NFD", lowered) if unicodedata.category(char) != "Mn"
    )
    return re.sub(r"[^a-z0-9 ]+", " ", no_accents).strip()


def muscle_group_of(name: str) -> str | None:
    normalized = _normalize(name)
    for group, keywords in _MUSCLE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized:
                return group
    return None


def normalize_exercise_name(name: str) -> str:
    return _normalize(name)
