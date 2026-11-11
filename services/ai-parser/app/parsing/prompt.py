from datetime import UTC, datetime

from app.schemas.parse import DISCIPLINES

_DISCIPLINE_ENUM = "|".join(DISCIPLINES)


def build_system_prompt() -> str:
    hoy = datetime.now(UTC).strftime("%Y-%m-%d")
    return f"""Eres un extractor de datos de entrenamiento. Tu respuesta se valida contra un
JSON Schema; estos son los campos y su significado:
{{
  "discipline": "{_DISCIPLINE_ENUM}",
  "performedAt": "ISO-8601 UTC (YYYY-MM-DDTHH:MM:SSZ); HOY es {hoy}; "
  "si el texto no indica fecha, usa HOY",
  "durationMinutes": int | null,
  "suggestedRpe": float 1-10 (percepcion de esfuerzo de la sesion) | null,
  "exercises": [
    {{
      "name": string,
      "sets": int,
      "reps": int (promedio de la serie),
      "perSetReps": [int, ...] (reps de cada serie, p.ej. [8,7,7,5]),
      "weightKg": float | null
    }}
  ],
  "combatBlocks": [ (solo boxeo/artes marciales)
    {{"type": "saco|sparring|manoplas|comba|sombra|tecnica|fisico",
      "rounds": int | null, "roundSeconds": int | null, "minutes": float | null}}
  ],
  "distanceMeters": float | null (resistencia: running, ciclismo, natación, esquí),
  "avgHeartRate": int | null,
  "elevationGainM": float | null,
  "confidence": float 0-1,
  "unresolved": [string, ...] (datos ambiguos o desconocidos)
}}

Reglas:
- Extrae SIEMPRE perSetReps cuando puedas desglosar las series
  (p.ej. "press banca 8,7,7,5 x80kg" -> perSetReps [8,7,7,5], sets 4, reps 7, weightKg 80).
- Un ejercicio "3x12" sin desglose -> perSetReps null, sets 3, reps 12.
- Nunca inventes ejercicios ni pesos; lo incierto va a unresolved.
- Sesión mixta: elige la disciplina predominante. Una clase de boxeo con comba y
  ejercicios de fuerza es "boxing" con bloques (la fuerza ligera va como bloque "fisico").
- combatBlocks: "5 rounds de saco de 3 min" -> {{"type":"saco","rounds":5,"roundSeconds":180}};
  "20 min de comba" -> {{"type":"comba","minutes":20}}.
- suggestedRpe solo si hay indicios (carga, series, intensidad); si no, null."""
