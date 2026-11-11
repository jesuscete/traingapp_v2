from typing import Literal

from pydantic import BaseModel, Field


class AgentTool(BaseModel):
    name: str
    description: str
    parameters: dict[str, str] = Field(default_factory=dict)  # nombre -> descripción
    writes: bool = False  # True = solo propone; el usuario confirma


class AgentMessage(BaseModel):
    role: Literal["usuario", "asistente", "herramienta"]
    content: str
    tool: str | None = None


class AgentStepRequest(BaseModel):
    context: dict[str, object] = Field(default_factory=dict)
    tools: list[AgentTool] = Field(default_factory=list)
    messages: list[AgentMessage] = Field(min_length=1)
    force_answer: bool = Field(default=False, alias="forceAnswer")


class AgentStepResponse(BaseModel):
    source: Literal["llm", "fallback"] = "llm"
    action: Literal["responder", "herramienta"]
    tool: str | None = None
    arguments: dict[str, object] = Field(default_factory=dict)
    message: str = ""
