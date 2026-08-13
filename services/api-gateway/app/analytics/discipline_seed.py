"""Catalogo canonico de disciplinas de entrenamiento.

Fuente de verdad de la tabla `discipline`: (name, normalized_name, met,
category, kind). `met` es el valor MET del Compendium (kcal por hora por kg de
peso corporal); `kind` distingue el tratamiento analitico: "gym" (trabajo
mecanico con ejercicios) frente a "cardio" (estimacion por MET). La carga
muscular de cada disciplina vive en `fatigue.MUSCLE_LOAD_DEFAULT` y se
sembrada en `discipline_muscle_load`.
"""

# (name, normalized_name, met, category, kind)
DISCIPLINE_SEED: tuple[tuple[str, str, float, str, str], ...] = (
    ("Gimnasio", "gym", 5.0, "gimnasio", "gym"),
    ("Calistenia", "calisthenics", 5.5, "gimnasio", "cardio"),
    ("Boxeo", "boxing", 7.8, "combate", "cardio"),
    ("Artes marciales", "martial_arts", 7.5, "combate", "cardio"),
    ("Running", "running", 8.2, "cardio", "cardio"),
    ("Ciclismo", "cycling", 7.1, "cardio", "cardio"),
    ("Natación", "swimming", 6.0, "cardio", "cardio"),
    ("Escalada", "climbing", 6.0, "cardio", "cardio"),
    ("Fútbol", "football", 7.0, "equipo", "cardio"),
    ("Baloncesto", "basketball", 6.5, "equipo", "cardio"),
    ("Voleibol", "volleyball", 4.5, "equipo", "cardio"),
    ("Cricket", "cricket", 4.0, "equipo", "cardio"),
    ("Béisbol", "baseball", 5.0, "equipo", "cardio"),
    ("Hockey", "hockey", 7.5, "equipo", "cardio"),
    ("Rugby", "rugby", 7.0, "equipo", "cardio"),
    ("Balonmano", "handball", 7.0, "equipo", "cardio"),
    ("Bádminton", "badminton", 5.5, "raqueta", "cardio"),
    ("Tenis de mesa", "table_tennis", 4.0, "raqueta", "cardio"),
    ("Tenis", "tennis", 7.3, "raqueta", "cardio"),
    ("Esquí / snowboard", "ski_snowboard", 5.3, "invierno", "cardio"),
    ("Golf", "golf", 3.5, "otros", "cardio"),
    ("Otro", "other", 4.0, "otros", "cardio"),
)

# Etiquetas de `category` para la UI.
CATEGORY_LABELS: dict[str, str] = {
    "gimnasio": "Gimnasio",
    "combate": "Combate",
    "cardio": "Cardio / resistencia",
    "equipo": "Deportes de equipo",
    "raqueta": "De raqueta",
    "invierno": "Invierno",
    "otros": "Otros",
}
