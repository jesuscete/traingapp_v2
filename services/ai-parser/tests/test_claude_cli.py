import asyncio
import json
import sys
from pathlib import Path

import pytest

from app.llm.claude_cli import ClaudeCliProvider, _structured_output
from app.llm.errors import LLMError, LLMTimeoutError

SCHEMA: dict[str, object] = {"type": "object", "properties": {"ok": {"type": "boolean"}}}


def _fake_cli(tmp_path: Path, body: str) -> str:
    """Script Python que hace de `claude`: registra argv/stdin y ejecuta `body`."""
    script = tmp_path / "fake_claude.py"
    script.write_text(
        "import json, sys\n"
        "args = sys.argv[1:]\n"
        "prompt = sys.stdin.buffer.read().decode('utf-8')\n"
        f"{body}\n",
        encoding="utf-8",
    )
    launcher = tmp_path / ("fake_claude.cmd" if sys.platform == "win32" else "fake_claude")
    if sys.platform == "win32":
        launcher.write_text(f'@"{sys.executable}" "{script}" %*\n', encoding="utf-8")
    else:
        launcher.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{script}" "$@"\n')
        launcher.chmod(0o755)
    return str(launcher)


def test_structured_output_envelope() -> None:
    ok = json.dumps({"is_error": False, "structured_output": {"ok": True}}).encode()
    assert _structured_output(ok) == {"ok": True}
    with pytest.raises(LLMError):
        _structured_output(json.dumps({"is_error": True, "result": "rate limit"}).encode())
    with pytest.raises(LLMError):
        _structured_output(json.dumps({"is_error": False, "result": "texto"}).encode())
    with pytest.raises(LLMError):
        _structured_output(b"no json")


def test_provider_sends_flags_prompt_and_reads_output(tmp_path: Path) -> None:
    record = tmp_path / "record.json"
    body = (
        "system_file = args[args.index('--system-prompt-file') + 1]\n"
        f"open(r'{record}', 'w', encoding='utf-8').write(json.dumps({{"
        "'args': args, 'prompt': prompt, "
        "'system': open(system_file, encoding='utf-8').read()}))\n"
        "print(json.dumps({'is_error': False, 'structured_output': {'ok': True}}))"
    )
    provider = ClaudeCliProvider(executable=_fake_cli(tmp_path, body), model="haiku", timeout=30)
    result = asyncio.run(provider.complete_json("SISTEMA", "datos ñ", schema=SCHEMA))
    assert result == {"ok": True}
    seen = json.loads(record.read_text(encoding="utf-8"))
    args = seen["args"]
    assert args[args.index("--model") + 1] == "haiku"
    assert json.loads(args[args.index("--json-schema") + 1]) == SCHEMA
    assert "--no-session-persistence" in args and "--tools" in args
    assert seen["prompt"] == "datos ñ"
    assert seen["system"] == "SISTEMA"


def test_provider_non_zero_exit_raises(tmp_path: Path) -> None:
    provider = ClaudeCliProvider(
        executable=_fake_cli(tmp_path, "sys.stderr.write('auth error'); sys.exit(2)"), timeout=30
    )
    with pytest.raises(LLMError, match="código 2"):
        asyncio.run(provider.complete_json("s", "u", schema=SCHEMA))


def test_provider_timeout_raises(tmp_path: Path) -> None:
    provider = ClaudeCliProvider(
        executable=_fake_cli(tmp_path, "import time; time.sleep(3)"), timeout=1
    )
    with pytest.raises(LLMTimeoutError):
        asyncio.run(provider.complete_json("s", "u", schema=SCHEMA))


def test_missing_executable_raises() -> None:
    provider = ClaudeCliProvider(executable="definitely-not-claude-xyz", timeout=5)
    with pytest.raises(LLMError):
        asyncio.run(provider.complete_json("s", "u", schema=SCHEMA))


def test_failure_reason_is_read_from_stdout_envelope() -> None:
    from app.llm.claude_cli import cli_failure
    from app.llm.errors import LLMUsageLimitError

    limit = json.dumps({"is_error": True, "result": "Claude AI usage limit reached"}).encode()
    assert isinstance(cli_failure(1, limit, b""), LLMUsageLimitError)
    status = json.dumps({"is_error": True, "result": "x", "api_error_status": 429}).encode()
    assert isinstance(cli_failure(1, status, b""), LLMUsageLimitError)
    other = cli_failure(1, json.dumps({"result": "Invalid model"}).encode(), b"")
    assert not isinstance(other, LLMUsageLimitError) and "Invalid model" in str(other)
    assert "boom" in str(cli_failure(2, b"no json", b"boom"))


def test_agent_explains_usage_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.llm import factory
    from app.llm.errors import LLMUsageLimitError
    from app.parsing.agent import USAGE_LIMIT, agent_step
    from app.schemas.agent import AgentMessage, AgentStepRequest

    class Limited:
        name = "claude_cli"

        async def complete_json(self, *args: object, **kwargs: object) -> dict[str, object]:
            raise LLMUsageLimitError("limit")

    monkeypatch.setattr(factory, "get_provider", lambda: Limited())
    body = AgentStepRequest(messages=[AgentMessage(role="usuario", content="hola")])
    step = asyncio.run(agent_step(body))
    assert step.message == USAGE_LIMIT and step.source == "fallback"
