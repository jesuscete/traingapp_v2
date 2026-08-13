import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, field_validator
from pydantic.alias_generators import to_camel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.catalog_seed import (
    MUSCLE_SEED,
    MUSCLE_ZONE_LABELS,
    MUSCLE_ZONE_MEMBERS,
    MUSCLE_ZONES,
)
from app.api.deps import get_current_user
from app.core.database import get_db
from app.crud import routine as routine_crud
from app.models import ExerciseCatalog, Muscle, User
from app.schemas.routine import DisciplineOut

router = APIRouter(prefix="/catalog", tags=["catalog"])


class CatalogExerciseOut(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )

    id: uuid.UUID
    name: str
    normalized_name: str
    exercise_type: str
    muscle_map: dict[str, float]
    uses_bodyweight: bool
    unilateral: bool
    images: list[str] = []
    details: dict[str, object] | None = None

    @field_validator("images", mode="before")
    @classmethod
    def _images_or_empty(cls, value: object) -> object:
        return value or []


@router.get("/exercises", response_model=list[CatalogExerciseOut])
async def list_catalog_exercises(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ExerciseCatalog]:
    result = await session.execute(
        select(ExerciseCatalog).order_by(ExerciseCatalog.name)
    )
    return list(result.scalars().all())


@router.get("/disciplines", response_model=list[DisciplineOut])
async def list_disciplines(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[DisciplineOut]:
    disciplines = await routine_crud.list_disciplines(session)
    return [DisciplineOut.model_validate(item) for item in disciplines]


class MuscleOut(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )

    id: uuid.UUID
    code: str
    label: str
    rollup_code: str
    zone_code: str


@router.get("/muscles", response_model=list[MuscleOut])
async def list_muscles(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[Muscle]:
    result = await session.execute(select(Muscle))
    muscles = list(result.scalars().all())
    seed_order = {
        code: index for index, (code, _, _) in enumerate(MUSCLE_SEED)
    }
    muscles.sort(
        key=lambda muscle: (
            seed_order.get(muscle.code, len(seed_order)),
            muscle.code,
        )
    )
    return muscles


class ZoneOut(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )

    code: str
    label: str
    order: int
    members: list[str]


@router.get("/zones", response_model=list[ZoneOut])
async def list_zones(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[ZoneOut]:
    return [
        ZoneOut(
            code=code,
            label=MUSCLE_ZONE_LABELS[code],
            order=index,
            members=list(MUSCLE_ZONE_MEMBERS[code]),
        )
        for index, (code, _, _) in enumerate(MUSCLE_ZONES)
    ]
