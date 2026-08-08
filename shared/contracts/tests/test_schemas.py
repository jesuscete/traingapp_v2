import json
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

SCHEMAS = Path(__file__).parents[1] / "schemas"


def _load(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def _registry() -> Registry:
    resources: dict[str, Resource] = {}
    for path in SCHEMAS.glob("*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        resources[doc["$id"]] = Resource.from_contents(doc)
    return Registry(resources)


def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(_load(name), registry=_registry())


def test_schemas_are_valid() -> None:
    for path in SCHEMAS.glob("*.json"):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def test_training_session_gym_example() -> None:
    example = {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "userId": "550e8400-e29b-41d4-a716-446655440001",
        "discipline": "gym",
        "rawText": "5x5 press banca 80kg",
        "performedAt": "2026-08-07T18:30:00Z",
        "durationMinutes": 60,
        "volumeKg": 2000,
        "exercises": [
            {"name": "press banca", "sets": 5, "reps": 5, "weightKg": 80, "volumeKg": 2000}
        ],
    }
    _validator("training-session.json").validate(example)


def test_training_session_boxing_example() -> None:
    example = {
        "id": "550e8400-e29b-41d4-a716-446655440002",
        "userId": "550e8400-e29b-41d4-a716-446655440001",
        "discipline": "boxing",
        "rawText": "clase de boxeo de 1h30m",
        "performedAt": "2026-08-07T19:00:00Z",
        "durationMinutes": 90,
        "volumeKg": 0,
        "exercises": [],
    }
    _validator("training-session.json").validate(example)


def test_workout_draft_example() -> None:
    example = {
        "requestId": "550e8400-e29b-41d4-a716-446655440003",
        "rawText": "5x5 press banca 80kg",
        "discipline": "gym",
        "performedAt": "2026-08-07T18:30:00Z",
        "confidence": 0.92,
        "unresolved": [],
        "exercises": [
            {"name": "press banca", "sets": 5, "reps": 5, "weightKg": 80, "volumeKg": 2000}
        ],
    }
    _validator("workout-draft.json").validate(example)
