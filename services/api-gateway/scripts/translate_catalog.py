"""Traduce nombres e instrucciones de free-exercise-db al español con el CLI de Claude.

Genera `data/exercises_es.json` ({sourceId: {nameEs, instructionsEs}}), que se
versiona y se aplica al catálogo con la migración correspondiente. Es reanudable:
solo traduce los ejercicios que aún no están en el fichero de salida.

Uso (desde services/api-gateway, con `claude` instalado y autenticado):
    .venv\\Scripts\\python -m scripts.translate_catalog [--model haiku] [--batch 50]
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SOURCE = DATA_DIR / "exercises.json"
TARGET = DATA_DIR / "exercises_es.json"
CALL_TIMEOUT_SECONDS = 300

SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "nameEs": {"type": "string"},
                    "instructionsEs": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "nameEs", "instructionsEs"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}

PROMPT = """Eres traductor especializado en entrenamiento de fuerza. Traduce al español de España
los ejercicios del JSON de abajo.
- nameEs: el nombre que usaría un entrenador en un gimnasio español (p. ej. "Barbell Bench Press"
  -> "Press de banca con barra", "Lat Pulldown" -> "Jalón al pecho"). Mantén términos muy
  extendidos en inglés solo si es lo habitual (p. ej. "Hip thrust", "Face pull").
- instructionsEs: traduce cada paso, mismo número de pasos y mismo orden, tono claro e imperativo.
- Devuelve un item por cada id recibido, sin omitir ninguno.

EJERCICIOS:
{payload}"""


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


async def _translate_batch(batch: list[dict[str, Any]], model: str) -> dict[str, dict[str, Any]]:
    payload = json.dumps(
        [
            {"id": e["id"], "name": e["name"], "instructions": e.get("instructions") or []}
            for e in batch
        ],
        ensure_ascii=False,
    )
    process = await asyncio.create_subprocess_exec(
        "claude",
        "-p",
        "--model",
        model,
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(SCHEMA),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(
        process.communicate(PROMPT.format(payload=payload).encode("utf-8")),
        timeout=CALL_TIMEOUT_SECONDS,
    )
    if process.returncode != 0:
        raise RuntimeError(f"claude salió con {process.returncode}: {stderr.decode()[:500]}")
    envelope = json.loads(stdout)
    if envelope.get("is_error"):
        raise RuntimeError(f"claude devolvió error: {envelope.get('result')}")
    items = envelope["structured_output"]["items"]
    expected = {e["id"] for e in batch}
    return {
        item["id"]: {"nameEs": item["nameEs"], "instructionsEs": item["instructionsEs"]}
        for item in items
        if item["id"] in expected
    }


async def main(model: str, batch_size: int, concurrency: int) -> int:
    source: list[dict[str, Any]] = _load_json(SOURCE)
    done: dict[str, dict[str, Any]] = _load_json(TARGET) or {}
    pending = [e for e in source if e["id"] not in done]
    batches = [pending[i : i + batch_size] for i in range(0, len(pending), batch_size)]
    print(f"Pendientes: {len(pending)} ejercicios en {len(batches)} lotes", flush=True)

    semaphore = asyncio.Semaphore(concurrency)
    lock = asyncio.Lock()
    failures = 0

    async def run(index: int, batch: list[dict[str, Any]]) -> None:
        nonlocal failures
        async with semaphore:
            try:
                result = await _translate_batch(batch, model)
            except (RuntimeError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
                failures += 1
                print(f"  lote {index + 1}: FALLO ({exc})", file=sys.stderr, flush=True)
                return
        async with lock:
            done.update(result)
            TARGET.write_text(
                json.dumps(dict(sorted(done.items())), ensure_ascii=False, indent=1),
                encoding="utf-8",
            )
        missing = len(batch) - len(result)
        print(
            f"  lote {index + 1}/{len(batches)}: {len(result)} ok, {missing} sin traducir",
            flush=True,
        )

    await asyncio.gather(*(run(i, b) for i, b in enumerate(batches)))
    print(f"Traducidos: {len(done)}/{len(source)} · lotes fallidos: {failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="haiku")
    parser.add_argument("--batch", type=int, default=50)
    parser.add_argument("--concurrency", type=int, default=3)
    args = parser.parse_args()
    sys.exit(asyncio.run(main(args.model, args.batch, args.concurrency)))
