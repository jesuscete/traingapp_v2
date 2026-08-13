import asyncio

from app.llm.base import LLMProvider
from app.parsing.review import review_routine_with_llm
from app.parsing.review_service import (
    review_routine,
    review_routine_deterministic,
)

_PAYLOAD = [
    {
        "dia": "Lunes",
        "tipo": "gimnasio",
        "nombre": "Press de banca",
        "gruposMusculares": ["Pecho", "Tríceps", "Hombros"],
        "series": 4,
        "repsObjetivo": [8, 8, 6, 6],
        "volumenEstimado": 28,
    },
    {
        "dia": "Miércoles",
        "tipo": "deporte",
        "nombre": "Boxeo",
        "gruposMusculares": ["Hombros", "Core", "Tríceps", "Bíceps"],
        "duracionMin": 60,
        "intensidad": "media",
    },
]

_GOOD_JSON = (
    '{"puntos_fuertes": ["Combina gimnasio y deporte"],'
    '"solapamientos": [{"descripcion": "Hombros y tríceps se cargan el lunes y el miércoles",'
    '"grupos": ["Hombros", "Tríceps"], "dias": ["Lunes", "Miércoles"]}],'
    '"sugerencias": ["Deja 48h entre el trabajo de hombro y las clases de boxeo"]}'
)


class FakeProvider(LLMProvider):
    name = "fake"

    def __init__(self, content: str = _GOOD_JSON, *, error: bool = False) -> None:
        self._content = content
        self._error = error

    async def complete(self, system: str, user: str) -> str:
        if self._error:
            raise RuntimeError("provider boom")
        return self._content


def test_review_routine_with_llm_json() -> None:
    result = asyncio.run(review_routine_with_llm(FakeProvider(), _PAYLOAD))
    assert result.puntos_fuertes == ["Combina gimnasio y deporte"]
    assert len(result.solapamientos) == 1
    solape = result.solapamientos[0]
    assert "miércoles" in solape.descripcion
    assert solape.grupos == ["Hombros", "Tríceps"]
    assert solape.dias == ["Lunes", "Miércoles"]
    assert "48h" in result.sugerencias[0]


def test_review_routine_with_llm_fenced_json() -> None:
    fenced = "```json\n" + _GOOD_JSON + "\n```"
    result = asyncio.run(review_routine_with_llm(FakeProvider(fenced), _PAYLOAD))
    assert result.puntos_fuertes[0].startswith("Combina")


def test_review_routine_with_llm_plain_solapamientos_dropped() -> None:
    content = (
        '{"puntos_fuertes": ["ok"],"solapamientos": ["texto libre"],'
        '"sugerencias": ["cambia"]}'
    )
    result = asyncio.run(review_routine_with_llm(FakeProvider(content), _PAYLOAD))
    assert result.puntos_fuertes == ["ok"]
    assert result.solapamientos == []
    assert result.sugerencias == ["cambia"]


def test_review_routine_deterministic() -> None:
    result = review_routine_deterministic(_PAYLOAD)
    assert result.solapamientos
    assert result.solapamientos[0].descripcion
    assert result.sugerencias


def test_review_routine_falls_back_to_stub(monkeypatch) -> None:
    from app.llm import factory

    monkeypatch.setattr(factory, "get_provider", lambda: FakeProvider(error=True))
    result = asyncio.run(review_routine(_PAYLOAD))
    assert result.puntos_fuertes
    assert "acumulación semanal" in result.solapamientos[0].descripcion


def test_review_routine_no_provider_uses_stub(monkeypatch) -> None:
    from app.llm import factory

    monkeypatch.setattr(factory, "get_provider", lambda: None)
    result = asyncio.run(review_routine(_PAYLOAD))
    assert result.sugerencias