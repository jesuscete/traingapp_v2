import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class AgentMessageIn(CamelModel):
    text: str = Field(min_length=1, max_length=2000)


class AgentActionOut(CamelModel):
    """Propuesta pendiente de confirmar por el usuario."""

    id: str
    type: Literal["save_workout", "swap_exercise", "add_exercise", "save_meal"]
    summary: str
    # save_workout se confirma con /chat/confirm usando este requestId.
    request_id: uuid.UUID | None = None


class AgentReplyOut(CamelModel):
    source: Literal["llm", "fallback"]
    reply: str
    actions: list[AgentActionOut] = []
    tools_used: list[str] = []


class AgentActionResultOut(CamelModel):
    message: str
