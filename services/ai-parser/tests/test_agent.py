import asyncio

from app.llm.errors import LLMError
from app.parsing.agent import agent_step, step_with_llm
from app.schemas.agent import AgentMessage, AgentStepRequest, AgentTool
from tests.fakes import TextFakeProvider


class Fake(TextFakeProvider):
    def __init__(self, content: str = "", *, error: bool = False) -> None:
        self._content = content
        self._error = error
        self.system = ""

    async def complete(self, system: str, user: str) -> str:
        self.system = system
        if self._error:
            raise LLMError("boom")
        return self._content


TOOLS = [
    AgentTool(name="get_fatigue", description="Fatiga actual."),
    AgentTool(
        name="log_workout", description="Registra.", parameters={"text": "texto"}, writes=True
    ),
]


def _request(**kw: object) -> AgentStepRequest:
    return AgentStepRequest(
        context={"hoy": "2026-11-12"},
        tools=TOOLS,
        messages=[AgentMessage(role="usuario", content="¿cómo voy de piernas?")],
        **kw,
    )


def test_tool_call_parses_arguments_and_marks_writes() -> None:
    content = (
        '{"action":"herramienta","tool":"log_workout","arguments_json":"{\\"text\\":\\"5x5\\"}"}'
    )
    provider = Fake(content)
    step = asyncio.run(step_with_llm(provider, _request()))
    assert (step.action, step.tool, step.arguments) == (
        "herramienta",
        "log_workout",
        {"text": "5x5"},
    )
    assert "log_workout [PROPONE]" in provider.system


def test_unknown_tool_or_forced_answer_becomes_reply() -> None:
    unknown = '{"action":"herramienta","tool":"borrar_todo","message":"vale"}'
    assert asyncio.run(step_with_llm(Fake(unknown), _request())).action == "responder"
    forced = '{"action":"herramienta","tool":"get_fatigue","message":"Tienes las piernas bien."}'
    provider = Fake(forced)
    step = asyncio.run(
        step_with_llm(
            provider, AgentStepRequest(**{**_request().model_dump(), "forceAnswer": True})
        )
    )
    assert step.action == "responder" and step.message == "Tienes las piernas bien."
    assert "Ya no puedes usar más herramientas" in provider.system


def test_bad_arguments_json_is_ignored() -> None:
    content = '{"action":"herramienta","tool":"get_fatigue","arguments_json":"no-json"}'
    assert asyncio.run(step_with_llm(Fake(content), _request())).arguments == {}


def test_fallback_when_llm_fails(monkeypatch) -> None:
    from app.llm import factory

    monkeypatch.setattr(factory, "get_provider", lambda: Fake(error=True))
    step = asyncio.run(agent_step(_request()))
    assert (step.source, step.action) == ("fallback", "responder")
