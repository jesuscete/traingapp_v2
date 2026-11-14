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


class CardItemOut(CamelModel):
    """Elemento de una tarjeta: un ejercicio, un grupo muscular, una comida…"""

    title: str
    subtitle: str | None = None
    badge: str | None = None
    detail: str | None = None
    image_url: str | None = None
    exercise_id: uuid.UUID | None = None
    value: float | None = None  # 0-100 para barras (fatiga, % de objetivo)


class CardSectionOut(CamelModel):
    title: str | None = None
    items: list[CardItemOut] = []


class ChatCardOut(CamelModel):
    """Respuesta estructurada que el chat pinta sin IA (rutina, fatiga, ejercicios…)."""

    type: Literal["routine", "fatigue", "exercises", "nutrition"]
    title: str
    subtitle: str | None = None
    sections: list[CardSectionOut] = []
    link: str | None = None
    link_label: str | None = None


class AgentReplyOut(CamelModel):
    # "rules" = respondido por el router determinista, sin llamar a la IA.
    source: Literal["llm", "fallback", "rules"]
    reply: str
    actions: list[AgentActionOut] = []
    tools_used: list[str] = []
    cards: list[ChatCardOut] = []
    # "guided": el mensaje pertenece al flujo guiado (/chat/draft: plan, entreno en vivo).
    handoff: Literal["guided"] | None = None


class AgentActionResultOut(CamelModel):
    message: str
