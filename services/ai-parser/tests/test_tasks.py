"""Modelo por tarea (M10): las tareas cortas usan el modelo rápido sin cambiar proveedores."""

import asyncio
from pathlib import Path

import pytest
from pydantic import BaseModel

from app.core.config import settings
from app.llm.claude_cli import ClaudeCliProvider
from app.llm.structured import generate
from app.llm.tasks import claude_model_for, current_task


class Out(BaseModel):
    ok: bool


class RecordingProvider:
    name = "recording"

    def __init__(self) -> None:
        self.tasks: list[str] = []

    async def complete_json(
        self, system: str, user: str, *, schema: object, max_tokens: int | None = None
    ) -> dict[str, object]:
        self.tasks.append(current_task.get())
        return {"ok": True}


def test_generate_exposes_the_task_to_the_provider() -> None:
    provider = RecordingProvider()
    asyncio.run(generate(provider, "s", "u", Out, task="meal"))
    assert provider.tasks == ["meal"]
    assert current_task.get() == "llm"  # se restaura al terminar


def test_fast_tasks_use_the_fast_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "llm_fast_tasks", "meal,parse")
    monkeypatch.setattr(settings, "claude_model_fast", "haiku")
    monkeypatch.setattr(settings, "claude_model", "sonnet")
    assert claude_model_for("meal") == "haiku"
    assert claude_model_for("agent") == "sonnet"


def test_cli_command_picks_model_by_task(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "llm_fast_tasks", "meal")
    provider = ClaudeCliProvider(executable="claude")
    token = current_task.set("meal")
    try:
        command = provider._command({}, tmp_path / "s.txt")
    finally:
        current_task.reset(token)
    assert command[command.index("--model") + 1] == settings.claude_model_fast
    explicit = ClaudeCliProvider(executable="claude", model="opus")
    assert explicit._command({}, tmp_path / "s.txt")[3] == "opus"
