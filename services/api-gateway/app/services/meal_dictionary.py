"""Diccionario de comidas que aprende (M10): texto libre -> alimentos, con la IA solo para lo
que no se conoce todavía.

    «dos tostadas con aceite y un café con leche»
      -> trocear: [2 × "tostadas con aceite", 1 × "cafe con leche"]
      -> buscar cada frase en `food_alias` (tuyo > compartido) y en tus alimentos
      -> lo que falte va a la IA UNA vez; su respuesta se guarda como alias compartido
      -> la próxima vez «café con leche» sale del diccionario, sin IA.
"""

import re
from dataclasses import dataclass

from app.analytics.catalog import normalize_exercise_name

_SPLIT = re.compile(r"\s*(?:,|;|\+|\n|\||\by\b|\bmas\b|\badem[aá]s\b)\s*", re.IGNORECASE)
_NUMBER = re.compile(r"^(\d+(?:[.,]\d+)?)\s*")
_WORD_NUMBERS = {
    "un": 1.0,
    "una": 1.0,
    "uno": 1.0,
    "dos": 2.0,
    "tres": 3.0,
    "cuatro": 4.0,
    "cinco": 5.0,
    "seis": 6.0,
    "medio": 0.5,
    "media": 0.5,
    "un par de": 2.0,
}
# Unidades con peso explícito (el número son gramos/ml).
_MASS_UNITS = {"g": 1.0, "gr": 1.0, "gramos": 1.0, "grs": 1.0, "kg": 1000.0, "ml": 1.0, "l": 1000.0}
# Medidas caseras: gramos aproximados por unidad.
HOUSEHOLD_UNITS = {
    "cucharada": 10.0,
    "cucharadas": 10.0,
    "cucharadita": 5.0,
    "cucharaditas": 5.0,
    "vaso": 200.0,
    "vasos": 200.0,
    "taza": 250.0,
    "tazas": 250.0,
    "puñado": 30.0,
    "punado": 30.0,
    "punados": 30.0,
    "rebanada": 30.0,
    "rebanadas": 30.0,
    "plato": 250.0,
    "platos": 250.0,
    "lata": 120.0,
    "latas": 120.0,
    "scoop": 30.0,
    "scoops": 30.0,
    "cacito": 30.0,
    "cacitos": 30.0,
}
_LEADING_WORDS = ("de ", "del ", "el ", "la ", "los ", "las ", "unos ", "unas ")
_FILLER = re.compile(
    r"^(?:(?:hoy|ayer|esta manana|para (?:desayunar|comer|cenar|merendar)|"
    r"he (?:comido|desayunado|cenado|merendado|tomado|bebido)|me he (?:comido|tomado|bebido)|"
    r"apunta(?:me)?|registra|anota|en el (?:desayuno|almuerzo|comida|cena)|"
    r"de (?:desayuno|cena|comida))\s+)+"
)


@dataclass(frozen=True)
class Phrase:
    raw: str  # fragmento tal cual
    key: str  # clave del diccionario (normalizada, sin cantidad)
    quantity: float  # unidades («dos tostadas» = 2)
    grams: float | None  # gramos explícitos («200 g de arroz»), si los hay
    unit_grams: float | None = None  # medida casera («un vaso de» = 200 g por unidad)


def _singular(word: str) -> str:
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def alias_key(text: str) -> str:
    """Clave estable: sin tildes, minúsculas, sin artículos iniciales y en singular."""
    normalized = normalize_exercise_name(text)
    for lead in _LEADING_WORDS:
        if normalized.startswith(lead):
            normalized = normalized[len(lead) :]
    return " ".join(_singular(w) for w in normalized.split())


def parse_phrase(raw: str) -> Phrase | None:
    text = normalize_exercise_name(raw)
    text = _FILLER.sub("", text).strip()
    if not text:
        return None
    quantity = 1.0
    grams: float | None = None
    unit_grams: float | None = None
    match = _NUMBER.match(text)
    if match:
        quantity = float(match.group(1).replace(",", "."))
        text = text[match.end() :]
    else:
        for words, value in sorted(_WORD_NUMBERS.items(), key=lambda kv: -len(kv[0])):
            if text.startswith(words + " "):
                quantity = value
                text = text[len(words) + 1 :]
                break
    first, _, rest = text.partition(" ")
    if first in _MASS_UNITS and rest:
        grams = quantity * _MASS_UNITS[first]
        quantity = 1.0
        text = rest
    elif first in HOUSEHOLD_UNITS and rest:
        unit_grams = HOUSEHOLD_UNITS[first]
        text = rest
    key = alias_key(text)
    if not key:
        return None
    return Phrase(raw=raw.strip(), key=key, quantity=quantity, grams=grams, unit_grams=unit_grams)


def split_phrases(text: str) -> list[Phrase]:
    phrases = [parse_phrase(part) for part in _SPLIT.split(text) if part and part.strip()]
    return [p for p in phrases if p is not None]


def scale_items(phrase: Phrase, unit_items: list[dict[str, object]]) -> list[tuple[str, float]]:
    """Alimentos de UNA unidad del alias -> gramos para esta frase."""
    per_unit = [(str(i["food_id"]), float(str(i["grams"]))) for i in unit_items]
    total_unit = sum(g for _, g in per_unit) or 1.0
    if phrase.grams is not None:
        factor = phrase.grams / total_unit
    elif phrase.unit_grams is not None:
        factor = phrase.unit_grams * phrase.quantity / total_unit
    else:
        factor = phrase.quantity
    return [(food_id, round(g * factor, 1)) for food_id, g in per_unit]
