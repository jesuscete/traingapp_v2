"""Un paso del agente conversacional: responder o pedir una herramienta.

El bucle y la ejecución de herramientas viven en el api-gateway (tiene los datos).
Aquí solo se decide el siguiente paso con salida estructurada validada.
"""

import json
import logging
from typing import Literal

from pydantic import BaseModel, Field

from app.llm import factory
from app.llm.base import LLMProvider
from app.llm.errors import LLMError, LLMUsageLimitError
from app.llm.structured import generate, user_data, with_user_data_rule
from app.schemas.agent import AgentMessage, AgentStepRequest, AgentStepResponse, AgentTool

logger = logging.getLogger(__name__)

UNAVAILABLE = (
    "El asistente de IA no está disponible ahora mismo. Mientras tanto puedes registrar "
    "el entreno en «Entrenar → Registrar actividad» o importar el archivo del reloj."
)
USAGE_LIMIT = (
    "Se ha alcanzado el límite de uso de Claude (se renueva cada pocas horas). Mientras "
    "tanto puedes registrar el entreno en «Entrenar → Registrar actividad», importar el "
    "archivo del reloj o apuntar comidas en «Comidas»; todo lo demás funciona sin IA."
)

SYSTEM_PROMPT = """
Eres el entrenador personal de la app TrainingApp: preparación física para el deporte
principal del usuario (sobre todo boxeo), gimnasio, fatiga y recuperación. Hablas en
español, directo y cercano, con respuestas breves (máximo ~120 palabras salvo que pidan
detalle).

En cada paso decides UNA cosa:
- "herramienta": necesitas datos o quieres proponer un cambio. Indica "tool" y
  "arguments_json" (objeto JSON con los parámetros, como texto).
- "responder": ya puedes contestar al usuario en "message".

Reglas:
- Usa herramientas para cualquier dato del usuario (fatiga, sesiones, rutina, análisis);
  nunca inventes cifras.
- Las herramientas marcadas [PROPONE] no ejecutan nada: crean una propuesta que el usuario
  confirmará con un botón. Tras usarlas, dile qué has propuesto y que lo confirme.
- Para registrar un entreno contado en lenguaje natural usa la herramienta de registrar con
  el texto del usuario.
- Si falta información imprescindible, pregunta en vez de suponer.
""".strip()


class LlmAgentStep(BaseModel):
    action: Literal["responder", "herramienta"]
    tool: str | None = None
    arguments_json: str | None = None
    message: str = Field(default="")


def _render_tools(tools: list[AgentTool]) -> str:
    lines = []
    for tool in tools:
        params = ", ".join(f"{k}: {v}" for k, v in tool.parameters.items()) or "sin parámetros"
        tag = " [PROPONE]" if tool.writes else ""
        lines.append(f"- {tool.name}{tag}: {tool.description} Parámetros: {params}.")
    return "\n".join(lines)


def _render_messages(messages: list[AgentMessage]) -> str:
    parts = []
    for m in messages:
        label = f"herramienta {m.tool}" if m.role == "herramienta" else m.role
        parts.append(f"[{label}]\n{m.content}")
    return "\n\n".join(parts)


def _system(body: AgentStepRequest) -> str:
    context = json.dumps(body.context, ensure_ascii=False)
    system = (
        f"{SYSTEM_PROMPT}\n\nCONTEXTO: {context}\n\nHERRAMIENTAS DISPONIBLES:\n"
        f"{_render_tools(body.tools)}"
    )
    if body.force_answer:
        system += "\n\nYa no puedes usar más herramientas: responde ahora con lo que tienes."
    return with_user_data_rule(system)


def _arguments(raw: str | None) -> dict[str, object]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Agent arguments_json is not valid JSON: %s", raw[:200])
        return {}
    return data if isinstance(data, dict) else {}


async def step_with_llm(provider: LLMProvider, body: AgentStepRequest) -> AgentStepResponse:
    step = await generate(
        provider,
        _system(body),
        "Conversación hasta ahora:\n\n" + user_data(_render_messages(body.messages)),
        LlmAgentStep,
        task="agent",
    )
    known = {t.name for t in body.tools}
    if step.action == "herramienta" and not body.force_answer and step.tool in known:
        return AgentStepResponse(
            action="herramienta",
            tool=step.tool,
            arguments=_arguments(step.arguments_json),
            message=step.message.strip(),
        )
    message = step.message.strip() or "¿Puedes darme algo más de detalle?"
    return AgentStepResponse(action="responder", message=message)


async def agent_step(body: AgentStepRequest) -> AgentStepResponse:
    provider = factory.get_provider()
    if provider is None:
        return AgentStepResponse(source="fallback", action="responder", message=UNAVAILABLE)
    try:
        return await step_with_llm(provider, body)
    except LLMUsageLimitError:
        logger.warning("Agent step: límite de uso del proveedor (%s)", provider.name)
        return AgentStepResponse(source="fallback", action="responder", message=USAGE_LIMIT)
    except LLMError:
        logger.exception("Agent step failed (%s)", provider.name)
        return AgentStepResponse(source="fallback", action="responder", message=UNAVAILABLE)
