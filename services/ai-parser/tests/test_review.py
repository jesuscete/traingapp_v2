import asyncio

from app.llm.errors import LLMError
from app.parsing.review import review_routine_with_llm
from app.parsing.review_service import (
    review_routine,
    review_routine_deterministic,
)
from tests.fakes import TextFakeProvider

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


class FakeProvider(TextFakeProvider):
    name = "fake"

    def __init__(self, content: str = _GOOD_JSON, *, error: bool = False) -> None:
        self._content = content
        self._error = error

    async def complete(self, system: str, user: str) -> str:
        if self._error:
            raise LLMError("provider boom")
        return self._content


def test_review_routine_with_llm_caps_tokens() -> None:
    from app.core.config import settings

    provider = FakeProvider()
    asyncio.run(review_routine_with_llm(provider, _PAYLOAD))
    assert provider.last_max_tokens == settings.llm_review_max_tokens


def test_review_routine_with_llm_json() -> None:
    result = asyncio.run(review_routine_with_llm(FakeProvider(), _PAYLOAD))
    assert result.puntos_fuertes == ["Combina gimnasio y deporte"]
    assert len(result.solapamientos) == 1
    solape = result.solapamientos[0]
    assert "miércoles" in solape.descripcion
    assert solape.grupos == ["Hombros", "Tríceps"]
    assert solape.dias == ["Lunes", "Miércoles"]
    assert "48h" in result.sugerencias[0]


def test_review_routine_with_llm_rejects_plain_solapamientos() -> None:
    import pytest

    from app.llm.errors import LLMOutputError

    content = (
        '{"puntos_fuertes": ["ok"],"solapamientos": ["texto libre"],'
        '"sugerencias": ["cambia"]}'
    )
    provider = FakeProvider(content)
    with pytest.raises(LLMOutputError):
        asyncio.run(review_routine_with_llm(provider, _PAYLOAD))
    assert provider.calls == 2


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

def test_sport_narrative_llm_and_fallback(monkeypatch) -> None:
    from app.llm import factory
    from app.parsing.sport import narrate, narrate_with_llm

    analysis = {"score": 42, "gaps": [{"message": "Potencia rotacional: 0 series"}]}
    content = '{"resumen":"Te falta rotación para el golpeo.","prioridades":["Añade giros rusos"]}'
    result = asyncio.run(narrate_with_llm(FakeProvider(content), "Boxeo", analysis))
    assert (result.source, result.prioridades) == ("llm", ["Añade giros rusos"])

    monkeypatch.setattr(factory, "get_provider", lambda: FakeProvider(error=True))
    fallback = asyncio.run(narrate("Boxeo", analysis))
    assert fallback.source == "fallback"
    assert fallback.prioridades == ["Potencia rotacional: 0 series"]
    assert "42/100" in fallback.resumen
