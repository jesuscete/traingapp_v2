"""Proveedor Claude a través del CLI local (`claude -p`), ADR-002.

Usa la suscripción de Claude Code de la máquina. Sustituye el prompt de sistema de
Claude Code (`--system-prompt-file`), desactiva herramientas y persistencia, y pide
salida estructurada con `--json-schema` (llega en `structured_output`).
"""

import asyncio
import json
import tempfile
from pathlib import Path

from app.core.config import settings
from app.llm.base import JsonSchema
from app.llm.errors import LLMError, LLMTimeoutError

STDERR_EXCERPT = 500


class ClaudeCliProvider:
    name = "claude_cli"

    def __init__(
        self,
        *,
        executable: str = settings.claude_cli_path,
        model: str = settings.claude_model,
        timeout: float = settings.llm_timeout_seconds,
    ) -> None:
        self._executable = executable
        self._model = model
        self._timeout = timeout

    def _command(self, schema: JsonSchema, system_file: Path) -> list[str]:
        return [
            self._executable,
            "-p",
            "--model",
            self._model,
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
            detail = stderr.decode("utf-8", errors="replace")[:STDERR_EXCERPT]
            raise LLMError(f"claude terminó con código {process.returncode}: {detail}")
        return _structured_output(stdout)


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
