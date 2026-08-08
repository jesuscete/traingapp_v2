import uuid

from pydantic import BaseModel, Field


class ChatMessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class ChatEnqueueOut(BaseModel):
    requestId: uuid.UUID
    status: str
