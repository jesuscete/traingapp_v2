"""Agente más ligero (M10): al LLM solo le llegan los resultados de herramientas del turno."""

from app.services.agent import MAX_STORED_TOOL_CONTENT, _stored, context_messages


def test_previous_turn_tool_results_are_not_resent() -> None:
    history = [
        {"role": "usuario", "content": "¿qué me falta?"},
        {"role": "herramienta", "tool": "analisis_deporte", "content": "x" * 5000},
        {"role": "asistente", "content": "Te falta rotación."},
        {"role": "usuario", "content": "¿y el lunes?"},
        {"role": "herramienta", "tool": "ver_rutina", "content": "lunes: press banca"},
    ]
    sent = context_messages(history)
    tools = [m for m in sent if m["role"] == "herramienta"]
    assert [m["tool"] for m in tools] == ["ver_rutina"]
    assert "Te falta rotación." in [m["content"] for m in sent]


def test_stored_tool_results_are_trimmed() -> None:
    long = {"role": "herramienta", "tool": "t", "content": "y" * 5000}
    assert len(_stored(long)["content"]) <= MAX_STORED_TOOL_CONTENT + 20
    short = {"role": "asistente", "content": "z" * 5000}
    assert _stored(short) == short
