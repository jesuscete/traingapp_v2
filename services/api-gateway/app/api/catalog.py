import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
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
from app.core.config import settings
from app.core.database import get_db
from app.crud import catalog as catalog_crud
from app.crud import routine as routine_crud
from app.models import ExerciseCatalog, Muscle, User
from app.schemas.exercise_history import ExerciseHistoryOut
from app.schemas.routine import DisciplineOut
from app.services import exercise_history

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
    image_urls: list[str] = []
    is_favorite: bool = False
    details: dict[str, object] | None = None

    @field_validator("images", mode="before")
    @classmethod
    def _images_or_empty(cls, value: object) -> object:
        return value or []


def _image_url(path: str) -> str:
    if path.startswith(("http://", "https://")):
        return path
    return settings.exercise_image_base_url.rstrip("/") + "/" + path.lstrip("/")


@router.get("/exercises", response_model=list[CatalogExerciseOut])
async def list_catalog_exercises(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[CatalogExerciseOut]:
    result = await session.execute(
        select(ExerciseCatalog).order_by(ExerciseCatalog.name)
    )
    favorites = await catalog_crud.favorite_ids(session, current_user.id)
    out: list[CatalogExerciseOut] = []
    for exercise in result.scalars().all():
        item = CatalogExerciseOut.model_validate(exercise)
        item.image_urls = [_image_url(path) for path in item.images]
        item.is_favorite = exercise.id in favorites
        out.append(item)
    return out


async def _set_favorite(
    session: AsyncSession, user: User, exercise_id: uuid.UUID, *, favorite: bool
) -> None:
    if not await catalog_crud.exercise_exists(session, exercise_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    await catalog_crud.set_favorite(session, user.id, exercise_id, favorite=favorite)


@router.put("/exercises/{exercise_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def add_favorite(
    exercise_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    await _set_favorite(session, current_user, exercise_id, favorite=True)


@router.delete("/exercises/{exercise_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    exercise_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    await _set_favorite(session, current_user, exercise_id, favorite=False)


@router.get("/exercises/{exercise_id}/history", response_model=ExerciseHistoryOut)
async def get_exercise_history(
    exercise_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=200)] = 30,
) -> ExerciseHistoryOut:
    if not await catalog_crud.exercise_exists(session, exercise_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return await exercise_history.build_history(
        session, current_user.id, exercise_id, limit=limit
    )


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
