from app.parsing.stub import parse_text


def test_parse_gym_sets_reps() -> None:
    result = parse_text("5x5 press banca 80kg")
    assert result.discipline == "gym"
    assert result.durationMinutes is None
    assert result.confidence >= 0.9
    exercise = result.exercises[0]
    assert (exercise.sets, exercise.reps, exercise.weight_kg, exercise.name) == (
        5,
        5,
        80.0,
        "press banca",
    )


def test_parse_boxing_duration() -> None:
    result = parse_text("clase de boxeo de 1h30m")
    assert result.discipline == "boxing"
    assert result.durationMinutes == 90
    assert result.exercises == []


def test_parse_running_minutes() -> None:
    result = parse_text("carrera de 45 min")
    assert result.discipline == "running"
    assert result.durationMinutes == 45


def test_parse_decimal_weight() -> None:
    result = parse_text("3x8 sentadilla 102,5 kg")
    exercise = result.exercises[0]
    assert exercise.weight_kg == 102.5
    assert exercise.name == "sentadilla"


def test_parse_series_per_set() -> None:
    result = parse_text("press banca: 8,7,7,5 x80kg")
    exercise = result.exercises[0]
    assert exercise.per_set_reps == [8, 7, 7, 5]
    assert exercise.sets == 4
    assert exercise.reps == 7
    assert exercise.weight_kg == 80.0
    assert result.suggestedRpe == 8.0


def test_parse_series_per_set_parens_weight() -> None:
    result = parse_text("sentadilla: 10,10,8,6 (90 kg)")
    exercise = result.exercises[0]
    assert exercise.per_set_reps == [10, 10, 8, 6]
    assert exercise.weight_kg == 90.0


def test_suggested_rpe_cardio() -> None:
    result = parse_text("carrera de 45 min")
    assert result.suggestedRpe == 6.5


def test_parse_new_disciplines() -> None:
    assert parse_text("partido de futbol de 90 min").discipline == "football"
    assert parse_text("natacion en piscina 40 min").discipline == "swimming"
    assert parse_text("sesion de escalada 2h").discipline == "climbing"
    assert parse_text("tenis de mesa 1h").discipline == "table_tennis"
    assert parse_text("partido de tenis 1h").discipline == "tennis"
    assert parse_text("clase de karate 1h").discipline == "martial_arts"
    assert parse_text("esqui alpino 3h").discipline == "ski_snowboard"
