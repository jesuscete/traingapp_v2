"""Proveedor Claude a través del CLI local (`claude -p`), ADR-002.

Usa la suscripción de Claude Code de la máquina. Sustituye el prompt de sistema de
Claude Code (`--system-prompt-file`), desactiva herramientas y persistencia, y pide
salida estructurada con `--json-schema` (llega en `structured_output`).
"""

import asyncio
import json
import logging
import tempfile
import time
from pathlib import Path

from app.core.config import settings
from app.llm.base import JsonSchema
from app.llm.errors import LLMError, LLMTimeoutError, LLMUsageLimitError
from app.llm.tasks import claude_model_for, current_task

STDERR_EXCERPT = 500
logger = logging.getLogger(__name__)


class ClaudeCliProvider:
    name = "claude_cli"

    def __init__(
        self,
        *,
        executable: str = settings.claude_cli_path,
        model: str | None = None,
        timeout: float = settings.llm_timeout_seconds,
    ) -> None:
        self._executable = executable
        self._model = model  # None = modelo según la tarea (M10)
        self._timeout = timeout

    def _model_for_call(self) -> str:
        return self._model or claude_model_for(current_task.get())

    def _command(self, schema: JsonSchema, system_file: Path) -> list[str]:
        return [
            self._executable,
            "-p",
            "--model",
            self._model_for_call(),
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(schema, ensure_ascii=False),
            "--system-prompt-file",
            str(system_file),
            "--tools",
            "",
            "--no-session-persistence",
        ]

    async def complete_json(
        self,
        system: str,
        user: str,
        *,
        schema: JsonSchema,
        max_tokens: int | None = None,
    ) -> dict[str, object]:
        # max_tokens no se expone en el CLI; la longitud la acota el propio esquema.
        started = time.perf_counter()
        with tempfile.TemporaryDirectory(prefix="ai-parser-claude-") as workdir:
            system_file = Path(workdir) / "system.txt"
            system_file.write_text(system, encoding="utf-8")
            try:
                process = await asyncio.create_subprocess_exec(
                    *self._command(schema, system_file),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=workdir,  # evita que el CLI cargue CLAUDE.md/AGENTS.md del repo
                )
            except OSError as exc:
                raise LLMError(f"No se pudo ejecutar '{self._executable}': {exc}") from exc
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(user.encode("utf-8")), timeout=self._timeout
                )
            except TimeoutError as exc:
                process.kill()
                await process.wait()
                raise LLMTimeoutError(f"claude no respondió en {self._timeout}s") from exc
        if process.returncode != 0:
            raise cli_failure(process.returncode, stdout, stderr)
        output = _structured_output(stdout)
        _log_usage(stdout, self._model_for_call(), time.perf_counter() - started)
        return output


USAGE_LIMIT_HINTS = ("usage limit", "limit reached", "rate limit", "5-hour", "quota")


def cli_failure(code: int | None, stdout: bytes, stderr: bytes) -> LLMError:
    """El CLI explica el fallo en su JSON de salida (no en stderr): se rescata el motivo."""
    detail = stderr.decode("utf-8", errors="replace").strip()
    try:
        envelope = json.loads(stdout)
    except json.JSONDecodeError:
        envelope = None
    if isinstance(envelope, dict):
        detail = str(envelope.get("result") or detail)
        if envelope.get("api_error_status") == 429:
            return LLMUsageLimitError(f"Límite de uso de Claude: {detail[:STDERR_EXCERPT]}")
    if any(hint in detail.lower() for hint in USAGE_LIMIT_HINTS):
        return LLMUsageLimitError(f"Límite de uso de Claude: {detail[:STDERR_EXCERPT]}")
    return LLMError(f"claude terminó con código {code}: {detail[:STDERR_EXCERPT]}")


def _log_usage(stdout: bytes, model: str, seconds: float) -> None:
    """Medición permanente (M10): tarea, modelo, latencia y tokens de cada llamada."""
    try:
        envelope = json.loads(stdout)
    except json.JSONDecodeError:
        return
    usage = envelope.get("usage") if isinstance(envelope, dict) else None
    usage = usage if isinstance(usage, dict) else {}
    tokens_in = sum(
        int(usage.get(k) or 0)
        for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    )
    logger.info(
        "llm_call provider=claude_cli task=%s model=%s seconds=%.1f tokens_in=%d tokens_out=%s "
        "cost_usd=%s",
        current_task.get(),
        model,
        seconds,
        tokens_in,
        usage.get("output_tokens"),
        envelope.get("total_cost_usd") if isinstance(envelope, dict) else None,
    )


def _structured_output(stdout: bytes) -> dict[str, object]:
    try:
        envelope = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise LLMError("La salida de claude no es JSON") from exc
    if not isinstance(envelope, dict):
        raise LLMError("Envoltorio de claude inesperado")
    if envelope.get("is_error"):
        raise LLMError(f"claude devolvió un error: {str(envelope.get('result'))[:STDERR_EXCERPT]}")
    output = envelope.get("structured_output")
    if not isinstance(output, dict):
        raise LLMError("claude no devolvió structured_output")
    return output
