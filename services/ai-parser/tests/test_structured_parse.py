"""Entrenos escritos como lista clara de ejercicios: se resuelven sin IA (M10)."""

import asyncio

import pytest

from app.parsing import service
from app.parsing.stub import parse_structured


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "press banca 4x8 80kg, dominadas 3x10, remo 3x12 60kg",
            [("press banca", 4, 8, 80.0), ("dominadas", 3, 10, None), ("remo", 3, 12, 60.0)],
        ),
        ("4x8 press banca 80kg", [("press banca", 4, 8, 80.0)]),
        (
            "sentadilla 5x5 100 kg y prensa 3x12",
            [("sentadilla", 5, 5, 100.0), ("prensa", 3, 12, None)],
        ),
    ],
)
def test_structured_lists_are_parsed(text: str, expected: list[tuple]) -> None:
    result = parse_structured(text)
    assert result is not None and result.source == "rules"
    assert [(e.name, e.sets, e.reps, e.weight_kg) for e in result.exercises] == expected


@pytest.mark.parametrize(
    "text",
    [
        "Hoy hice pierna: sentadilla 5x5 100kg",
        "clase de boxeo de 1h30",
        "press banca 8,7,7,5 x80kg",
        "AMRAP 20: 5 dominadas, 10 flexiones",
    ],
)
def test_anything_ambiguous_goes_to_ai(text: str) -> None:
    assert parse_structured(text) is None


def test_service_skips_the_provider_for_structured_text(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom() -> None:
        raise AssertionError("no debería pedir proveedor LLM")

    monkeypatch.setattr(service.factory, "get_provider", boom)
    result = asyncio.run(service.parse_workout("press banca 4x8 80kg"))
    assert result.source == "rules"
