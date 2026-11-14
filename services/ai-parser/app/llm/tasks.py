"""Tarea en curso de cada llamada al LLM (M10): modelo por tarea y registro de uso.

`generate()` fija la tarea; el proveedor la consulta para elegir modelo (rápido o normal) y
para registrar tokens y latencia. Ningún proveedor necesita cambiar su firma.
"""

from contextvars import ContextVar

from app.core.config import settings

TASKS = ("agent", "meal", "parse", "plan", "splits", "review", "narrative")
current_task: ContextVar[str] = ContextVar("llm_task", default="llm")


def fast_tasks() -> frozenset[str]:
    return frozenset(t.strip() for t in settings.llm_fast_tasks.split(",") if t.strip())


def claude_model_for(task: str) -> str:
    return settings.claude_model_fast if task in fast_tasks() else settings.claude_model
