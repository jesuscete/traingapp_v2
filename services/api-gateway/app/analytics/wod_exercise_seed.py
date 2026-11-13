"""Movimientos de CrossFit y HYROX que faltaban en el catálogo.

Se guardan como los ejercicios importados (nombre canónico en inglés + `nameEs` en
`details`), así que NO cuentan como curados y no entran en la generación de rutinas de
gimnasio. `unit` indica cómo se mide: reps, distancia (m) o calorías.

muscles: activación por grupo (0-1, suma <= 1), igual que `exercise_seed`.
"""

from typing import Literal, TypedDict

WodUnit = Literal["reps", "distance", "calories"]


class WodExerciseSeed(TypedDict):
    name: str
    name_es: str
    category: Literal["crossfit", "hyrox"]
    unit: WodUnit
    muscles: dict[str, float]
    uses_bodyweight: bool


WOD_EXERCISE_SEED: tuple[WodExerciseSeed, ...] = (
    # --- HYROX (estaciones y carrera) ---
    {
        "name": "Wall Ball",
        "name_es": "Wall ball (lanzamiento a diana)",
        "category": "hyrox",
        "unit": "reps",
        "uses_bodyweight": False,
        "muscles": {
            "quadriceps": 0.3,
            "glutes": 0.2,
            "shoulders": 0.2,
            "core": 0.1,
            "triceps": 0.1,
            "hamstrings": 0.1,
        },
    },
    {
        "name": "Burpee Broad Jump",
        "name_es": "Burpee con salto horizontal",
        "category": "hyrox",
        "unit": "distance",
        "uses_bodyweight": True,
        "muscles": {
            "quadriceps": 0.3,
            "glutes": 0.2,
            "chest": 0.15,
            "shoulders": 0.1,
            "triceps": 0.1,
            "core": 0.1,
            "calves": 0.05,
        },
    },
    {
        "name": "Sandbag Lunges",
        "name_es": "Zancadas con saco",
        "category": "hyrox",
        "unit": "distance",
        "uses_bodyweight": False,
        "muscles": {
            "quadriceps": 0.35,
            "glutes": 0.3,
            "hamstrings": 0.15,
            "core": 0.1,
            "back": 0.1,
        },
    },
    {
        "name": "Sled Pull",
        "name_es": "Arrastre de trineo con cuerda (sled pull)",
        "category": "hyrox",
        "unit": "distance",
        "uses_bodyweight": False,
        "muscles": {
            "back": 0.35,
            "biceps": 0.2,
            "forearms": 0.2,
            "core": 0.1,
            "glutes": 0.1,
            "hamstrings": 0.05,
        },
    },
    {
        "name": "Rowing Machine",
        "name_es": "Remo ergómetro",
        "category": "hyrox",
        "unit": "distance",
        "uses_bodyweight": False,
        "muscles": {
            "back": 0.3,
            "quadriceps": 0.25,
            "glutes": 0.15,
            "biceps": 0.1,
            "hamstrings": 0.1,
            "core": 0.1,
        },
    },
    {
        "name": "SkiErg",
        "name_es": "SkiErg (ergómetro de esquí)",
        "category": "hyrox",
        "unit": "distance",
        "uses_bodyweight": False,
        "muscles": {"back": 0.3, "shoulders": 0.2, "triceps": 0.2, "core": 0.2, "quadriceps": 0.1},
    },
    {
        "name": "Run",
        "name_es": "Carrera",
        "category": "hyrox",
        "unit": "distance",
        "uses_bodyweight": True,
        "muscles": {
            "calves": 0.3,
            "quadriceps": 0.3,
            "hamstrings": 0.2,
            "glutes": 0.15,
            "core": 0.05,
        },
    },
    # --- CrossFit: cardio ---
    {
        "name": "Assault Bike",
        "name_es": "Bici de aire (Assault / Echo bike)",
        "category": "crossfit",
        "unit": "calories",
        "uses_bodyweight": False,
        "muscles": {
            "quadriceps": 0.4,
            "glutes": 0.15,
            "hamstrings": 0.15,
            "calves": 0.1,
            "shoulders": 0.1,
            "core": 0.1,
        },
    },
    {
        "name": "Single Unders",
        "name_es": "Comba (saltos simples)",
        "category": "crossfit",
        "unit": "reps",
        "uses_bodyweight": True,
        "muscles": {"calves": 0.6, "quadriceps": 0.15, "forearms": 0.15, "shoulders": 0.1},
    },
    {
        "name": "Double Unders",
        "name_es": "Dobles de comba (double unders)",
        "category": "crossfit",
        "unit": "reps",
        "uses_bodyweight": True,
        "muscles": {"calves": 0.6, "quadriceps": 0.15, "forearms": 0.15, "shoulders": 0.1},
    },
    # --- CrossFit: gimnásticos ---
    {
        "name": "Burpee",
        "name_es": "Burpee",
        "category": "crossfit",
        "unit": "reps",
        "uses_bodyweight": True,
        "muscles": {
            "chest": 0.25,
            "quadriceps": 0.2,
            "shoulders": 0.15,
            "triceps": 0.15,
            "core": 0.15,
            "glutes": 0.1,
        },
    },
    {
        "name": "Chest-to-Bar Pull-Up",
        "name_es": "Dominada pecho a la barra (C2B)",
        "category": "crossfit",
        "unit": "reps",
        "uses_bodyweight": True,
        "muscles": {"back": 0.45, "biceps": 0.2, "core": 0.15, "shoulders": 0.1, "forearms": 0.1},
    },
    {
        "name": "Toes-to-Bar",
        "name_es": "Pies a la barra (toes to bar)",
        "category": "crossfit",
        "unit": "reps",
        "uses_bodyweight": True,
        "muscles": {"core": 0.55, "forearms": 0.15, "back": 0.15, "shoulders": 0.15},
    },
    {
        "name": "Knees-to-Elbows",
        "name_es": "Rodillas al codo (knees to elbows)",
        "category": "crossfit",
        "unit": "reps",
        "uses_bodyweight": True,
        "muscles": {"core": 0.55, "forearms": 0.15, "back": 0.15, "shoulders": 0.15},
    },
    {
        "name": "Handstand Walk",
        "name_es": "Caminar en pino (handstand walk)",
        "category": "crossfit",
        "unit": "distance",
        "uses_bodyweight": True,
        "muscles": {"shoulders": 0.5, "triceps": 0.2, "core": 0.2, "forearms": 0.1},
    },
    {
        "name": "GHD Sit-Up",
        "name_es": "Abdominal en GHD",
        "category": "crossfit",
        "unit": "reps",
        "uses_bodyweight": True,
        "muscles": {"core": 0.75, "quadriceps": 0.25},
    },
    {
        "name": "Pistol Squat",
        "name_es": "Sentadilla pistol (a una pierna)",
        "category": "crossfit",
        "unit": "reps",
        "uses_bodyweight": True,
        "muscles": {"quadriceps": 0.5, "glutes": 0.3, "core": 0.1, "calves": 0.1},
    },
    # --- CrossFit: halterofilia y barra ---
    {
        "name": "Barbell Thruster",
        "name_es": "Thruster con barra",
        "category": "crossfit",
        "unit": "reps",
        "uses_bodyweight": False,
        "muscles": {
            "quadriceps": 0.35,
            "shoulders": 0.25,
            "glutes": 0.15,
            "triceps": 0.15,
            "core": 0.1,
        },
    },
    {
        "name": "Squat Snatch",
        "name_es": "Arrancada",
        "category": "crossfit",
        "unit": "reps",
        "uses_bodyweight": False,
        "muscles": {
            "quadriceps": 0.25,
            "glutes": 0.2,
            "shoulders": 0.2,
            "back": 0.15,
            "hamstrings": 0.1,
            "core": 0.1,
        },
    },
    {
        "name": "Power Snatch",
        "name_es": "Arrancada de potencia",
        "category": "crossfit",
        "unit": "reps",
        "uses_bodyweight": False,
        "muscles": {
            "glutes": 0.2,
            "shoulders": 0.2,
            "back": 0.2,
            "hamstrings": 0.15,
            "quadriceps": 0.15,
            "core": 0.1,
        },
    },
    {
        "name": "Squat Clean",
        "name_es": "Cargada",
        "category": "crossfit",
        "unit": "reps",
        "uses_bodyweight": False,
        "muscles": {
            "quadriceps": 0.3,
            "glutes": 0.2,
            "back": 0.2,
            "hamstrings": 0.15,
            "core": 0.1,
            "forearms": 0.05,
        },
    },
    {
        "name": "Clean and Jerk",
        "name_es": "Dos tiempos (clean & jerk)",
        "category": "crossfit",
        "unit": "reps",
        "uses_bodyweight": False,
        "muscles": {
            "quadriceps": 0.25,
            "glutes": 0.2,
            "shoulders": 0.2,
            "back": 0.15,
            "triceps": 0.1,
            "core": 0.1,
        },
    },
    {
        "name": "Split Jerk",
        "name_es": "Envión partido (split jerk)",
        "category": "crossfit",
        "unit": "reps",
        "uses_bodyweight": False,
        "muscles": {
            "shoulders": 0.35,
            "triceps": 0.25,
            "quadriceps": 0.2,
            "core": 0.1,
            "glutes": 0.1,
        },
    },
    {
        "name": "Barbell Overhead Squat",
        "name_es": "Sentadilla overhead con barra",
        "category": "crossfit",
        "unit": "reps",
        "uses_bodyweight": False,
        "muscles": {"quadriceps": 0.35, "shoulders": 0.2, "core": 0.2, "glutes": 0.15, "back": 0.1},
    },
    # --- CrossFit: kettlebell y mancuerna ---
    {
        "name": "American Kettlebell Swing",
        "name_es": "Swing americano con kettlebell",
        "category": "crossfit",
        "unit": "reps",
        "uses_bodyweight": False,
        "muscles": {
            "glutes": 0.3,
            "hamstrings": 0.25,
            "shoulders": 0.15,
            "back": 0.1,
            "core": 0.1,
            "forearms": 0.1,
        },
    },
    {
        "name": "Dumbbell Snatch",
        "name_es": "Arrancada con mancuerna",
        "category": "crossfit",
        "unit": "reps",
        "uses_bodyweight": False,
        "muscles": {
            "shoulders": 0.25,
            "glutes": 0.2,
            "hamstrings": 0.2,
            "back": 0.15,
            "core": 0.1,
            "quadriceps": 0.1,
        },
    },
    {
        "name": "Devil Press",
        "name_es": "Devil press",
        "category": "crossfit",
        "unit": "reps",
        "uses_bodyweight": False,
        "muscles": {
            "shoulders": 0.2,
            "glutes": 0.2,
            "chest": 0.15,
            "hamstrings": 0.15,
            "triceps": 0.1,
            "core": 0.1,
            "quadriceps": 0.1,
        },
    },
)
