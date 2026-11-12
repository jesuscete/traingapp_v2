import uuid
from datetime import date
from typing import Literal

from pydantic import Field

from app.schemas.session import CamelModel

GoalKind = Literal["weight", "event", "competition", "performance", "other"]


class GoalIn(CamelModel):
    kind: GoalKind
    title: str = Field(min_length=1, max_length=160)
    sport: str | None = Field(default=None, max_length=40)
    target_date: date | None = None
    target_value: float | None = None
    unit: str | None = Field(default=None, max_length=20)
    notes: str | None = Field(default=None, max_length=2000)
    is_primary: bool = False
    done: bool = False


class GoalOut(GoalIn):
    id: uuid.UUID
    days_left: int | None = None
