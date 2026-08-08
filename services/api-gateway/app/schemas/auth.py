import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

Goal = Literal["loss", "maintenance", "performance"]


class CamelModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(CamelModel):
    id: uuid.UUID
    email: EmailStr
    name: str
    weight_kg: float | None = None
    height_cm: float | None = None
    birth_year: int | None = None
    sex: Literal["male", "female"] | None = None
    goal: Goal | None = None
    sports: list[str] | None = None
    created_at: datetime


class ProfileIn(CamelModel):
    weight_kg: float | None = Field(default=None, ge=20, le=400)
    height_cm: float | None = Field(default=None, ge=80, le=250)
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    sex: Literal["male", "female"] | None = None
    goal: Goal | None = None
    sports: list[str] | None = None


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
