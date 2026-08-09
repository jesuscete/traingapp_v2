"""Seed canonico del catalogo de ejercicios (Chat Paso 1, ADR-0xx).

Cada entrada alimenta la tabla `exercise_catalog`:
- name: nombre visible (ej. "Press banca").
- normalized_name: clave unica, normalizada (minusculas, sin acentos).
- exercise_type: "gym" | "sport".
- muscles: activacion por grupo muscular (0-1, suma <= 1).
- uses_bodyweight: el ejercicio usa peso corporal (dominadas/fondos); el
  peso registrado por serie es solo el lastre anadido.
- unilateral: ejercicio unilateral (el lado se registra en cada set_entry).

Es la unica fuente: la migracion y los tests poblan la tabla desde aqui.
El evolutivo de importacion masiva de ejercicios (API externa) alimentara
esta misma estructura.
"""

EXERCISE_CATALOG_SEED: list[dict[str, object]] = [
    # --- Pecho / hombro / triceps ---
    {
        "name": "Press banca",
        "normalized_name": "press banca",
        "exercise_type": "gym",
        "muscles": {"chest": 0.60, "triceps": 0.30, "shoulders": 0.10},
    },
    {
        "name": "Press inclinado",
        "normalized_name": "press inclinado",
        "exercise_type": "gym",
        "muscles": {"chest": 0.55, "shoulders": 0.25, "triceps": 0.20},
    },
    {
        "name": "Press declinado",
        "normalized_name": "press declinado",
        "exercise_type": "gym",
        "muscles": {"chest": 0.65, "triceps": 0.25, "shoulders": 0.10},
    },
    {
        "name": "Aperturas",
        "normalized_name": "aperturas",
        "exercise_type": "gym",
        "muscles": {"chest": 0.80, "shoulders": 0.20},
    },
    {
        "name": "Fondos en paralelas",
        "normalized_name": "fondos en paralelas",
        "exercise_type": "gym",
        "uses_bodyweight": True,
        "muscles": {"chest": 0.50, "triceps": 0.40, "shoulders": 0.10},
    },
    {
        "name": "Press con mancuernas",
        "normalized_name": "press con mancuernas",
        "exercise_type": "gym",
        "muscles": {"chest": 0.55, "shoulders": 0.25, "triceps": 0.20},
    },
    {
        "name": "Press militar",
        "normalized_name": "press militar",
        "exercise_type": "gym",
        "muscles": {"shoulders": 0.70, "triceps": 0.20, "core": 0.10},
    },
    {
        "name": "Elevaciones laterales",
        "normalized_name": "elevaciones laterales",
        "exercise_type": "gym",
        "muscles": {"shoulders": 0.90, "neck": 0.10},
    },
    {
        "name": "Elevaciones frontales",
        "normalized_name": "elevaciones frontales",
        "exercise_type": "gym",
        "muscles": {"shoulders": 0.85, "chest": 0.15},
    },
    {
        "name": "Elevaciones posteriores",
        "normalized_name": "elevaciones posteriores",
        "exercise_type": "gym",
        "muscles": {"shoulders": 0.60, "back": 0.40},
    },
    # --- Espalda / biceps ---
    {
        "name": "Remo con barra",
        "normalized_name": "remo con barra",
        "exercise_type": "gym",
        "muscles": {"back": 0.60, "biceps": 0.20, "forearms": 0.20},
    },
    {
        "name": "Remo mancuerna",
        "normalized_name": "remo mancuerna",
        "exercise_type": "gym",
        "unilateral": True,
        "muscles": {"back": 0.55, "biceps": 0.20, "core": 0.15, "forearms": 0.10},
    },
    {
        "name": "Remo sentado",
        "normalized_name": "remo sentado",
        "exercise_type": "gym",
        "muscles": {"back": 0.65, "biceps": 0.20, "forearms": 0.15},
    },
    {
        "name": "Dominadas",
        "normalized_name": "dominadas",
        "exercise_type": "gym",
        "uses_bodyweight": True,
        "muscles": {"back": 0.70, "biceps": 0.20, "forearms": 0.10},
    },
    {
        "name": "Jalón al pecho",
        "normalized_name": "jalon al pecho",
        "exercise_type": "gym",
        "muscles": {"back": 0.70, "biceps": 0.20, "forearms": 0.10},
    },
    {
        "name": "Face pull",
        "normalized_name": "face pull",
        "exercise_type": "gym",
        "muscles": {"shoulders": 0.45, "back": 0.45, "biceps": 0.10},
    },
    # --- Pierna / gluteo / core ---
    {
        "name": "Peso muerto",
        "normalized_name": "peso muerto",
        "exercise_type": "gym",
        "muscles": {
            "glutes": 0.35,
            "back": 0.30,
            "hamstrings": 0.20,
            "quadriceps": 0.10,
            "core": 0.05,
        },
    },
    {
        "name": "Peso muerto rumano",
        "normalized_name": "peso muerto rumano",
        "exercise_type": "gym",
        "muscles": {"hamstrings": 0.55, "glutes": 0.30, "back": 0.15},
    },
    {
        "name": "Sentadilla",
        "normalized_name": "sentadilla",
        "exercise_type": "gym",
        "muscles": {"quadriceps": 0.50, "glutes": 0.30, "hamstrings": 0.10, "core": 0.10},
    },
    {
        "name": "Sentadilla frontal",
        "normalized_name": "sentadilla frontal",
        "exercise_type": "gym",
        "muscles": {"quadriceps": 0.50, "core": 0.20, "glutes": 0.20, "back": 0.10},
    },
    {
        "name": "Prensa",
        "normalized_name": "prensa",
        "exercise_type": "gym",
        "muscles": {"quadriceps": 0.60, "glutes": 0.30, "hamstrings": 0.10},
    },
    {
        "name": "Zancadas",
        "normalized_name": "zancadas",
        "exercise_type": "gym",
        "unilateral": True,
        "muscles": {"quadriceps": 0.45, "glutes": 0.35, "hamstrings": 0.20},
    },
    {
        "name": "Extensión de cuádriceps",
        "normalized_name": "extension de cuadriceps",
        "exercise_type": "gym",
        "muscles": {"quadriceps": 0.90, "core": 0.10},
    },
    {
        "name": "Curl femoral",
        "normalized_name": "curl femoral",
        "exercise_type": "gym",
        "muscles": {"hamstrings": 0.90, "glutes": 0.10},
    },
    {
        "name": "Hip thrust",
        "normalized_name": "hip thrust",
        "exercise_type": "gym",
        "muscles": {"glutes": 0.80, "hamstrings": 0.15, "core": 0.05},
    },
    {
        "name": "Gemelos",
        "normalized_name": "gemelos",
        "exercise_type": "gym",
        "muscles": {"calves": 0.90, "quadriceps": 0.10},
    },
    {
        "name": "Elevación de talones",
        "normalized_name": "elevacion de talones",
        "exercise_type": "gym",
        "muscles": {"calves": 0.90, "quadriceps": 0.10},
    },
    # --- Biceps / triceps / antebrazo ---
    {
        "name": "Curl bíceps",
        "normalized_name": "curl biceps",
        "exercise_type": "gym",
        "muscles": {"biceps": 0.80, "forearms": 0.20},
    },
    {
        "name": "Curl martillo",
        "normalized_name": "curl martillo",
        "exercise_type": "gym",
        "muscles": {"biceps": 0.60, "forearms": 0.40},
    },
    {
        "name": "Press francés",
        "normalized_name": "press frances",
        "exercise_type": "gym",
        "muscles": {"triceps": 0.85, "shoulders": 0.15},
    },
    {
        "name": "Push down",
        "normalized_name": "push down",
        "exercise_type": "gym",
        "muscles": {"triceps": 0.90, "forearms": 0.10},
    },
    {
        "name": "Extensiones de tríceps",
        "normalized_name": "extensiones de triceps",
        "exercise_type": "gym",
        "muscles": {"triceps": 0.90, "forearms": 0.10},
    },
    # --- Core ---
    {
        "name": "Plancha",
        "normalized_name": "plancha",
        "exercise_type": "gym",
        "uses_bodyweight": True,
        "muscles": {"core": 0.85, "shoulders": 0.15},
    },
    {
        "name": "Crunches",
        "normalized_name": "crunches",
        "exercise_type": "gym",
        "muscles": {"core": 0.90, "quadriceps": 0.10},
    },
    {
        "name": "Russian twist",
        "normalized_name": "russian twist",
        "exercise_type": "gym",
        "muscles": {"core": 0.85, "quadriceps": 0.15},
    },
    {
        "name": "Elevación de piernas",
        "normalized_name": "elevacion de piernas",
        "exercise_type": "gym",
        "muscles": {"core": 0.80, "quadriceps": 0.20},
    },
]
