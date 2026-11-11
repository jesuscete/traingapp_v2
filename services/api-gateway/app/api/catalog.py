import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
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
from app.crud import catalog as catalog_crud
from app.crud import routine as routine_crud
from app.models import ExerciseCatalog, Muscle, User
from app.schemas.exercise_history import ExerciseHistoryOut
from app.schemas.routine import DisciplineOut
from app.schemas.sport_analysis import AlternativeOut
from app.services import exercise_history
from app.services.sport_analysis import alternatives, image_url

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
    is_custom: bool = False
    details: dict[str, object] | None = None

    @field_validator("images", mode="before")
    @classmethod
    def _images_or_empty(cls, value: object) -> object:
        return value or []


@router.get("/exercises", response_model=list[CatalogExerciseOut])
async def list_catalog_exercises(
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[CatalogExerciseOut]:
    exercises = await catalog_crud.list_visible(session, current_user.id)
    favorites = await catalog_crud.favorite_ids(session, current_user.id)
    return [_exercise_out(exercise, favorites) for exercise in exercises]


def _exercise_out(exercise: ExerciseCatalog, favorites: set[uuid.UUID]) -> CatalogExerciseOut:
    item = CatalogExerciseOut.model_validate(exercise)
    item.image_urls = [image_url(path) for path in item.images]
    item.is_favorite = exercise.id in favorites
    item.is_custom = exercise.owner_user_id is not None
    return item


MuscleGroup = Literal[
    "back",
    "biceps",
    "calves",
    "chest",
    "core",
    "forearms",
    "glutes",
    "hamstrings",
    "neck",
    "quadriceps",
    "shoulders",
    "triceps",
]
PRIMARY_ACTIVATION = 1.0
SECONDARY_ACTIVATION = 0.5


class CustomExerciseIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    name: str = Field(min_length=2, max_length=120)
    primary_muscles: list[MuscleGroup] = Field(min_length=1, max_length=4)
    secondary_muscles: list[MuscleGroup] = Field(default_factory=list, max_length=6)
    equipment: str | None = Field(default=None, max_length=40)
    category: str = Field(default="strength", max_length=40)
    uses_bodyweight: bool = False
    unilateral: bool = False
    instructions: list[str] = Field(default_factory=list, max_length=20)


@router.post("/exercises", response_model=CatalogExerciseOut, status_code=status.HTTP_201_CREATED)
async def create_custom_exercise(
    body: CustomExerciseIn,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CatalogExerciseOut:
    muscle_map: dict[str, float] = {m: SECONDARY_ACTIVATION for m in body.secondary_muscles}
    muscle_map.update({m: PRIMARY_ACTIVATION for m in body.primary_muscles})
    try:
        exercise = await catalog_crud.create_custom(
            session,
            current_user.id,
            name=body.name,
            muscle_map=muscle_map,
            uses_bodyweight=body.uses_bodyweight,
            unilateral=body.unilateral,
            details={
                "source": "custom",
                "category": body.category,
                "equipment": body.equipment,
                "instructions": [i.strip() for i in body.instructions if i.strip()],
                "primaryMuscles": list(body.primary_muscles),
                "secondaryMuscles": list(body.secondary_muscles),
            },
        )
    except catalog_crud.CustomExerciseNameTaken:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Ya existe un ejercicio con ese nombre"
        ) from None
    return _exercise_out(exercise, set())


@router.delete("/exercises/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_exercise(
    exercise_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    result = await catalog_crud.delete_custom(session, current_user.id, exercise_id)
    if result is catalog_crud.DeleteResult.NOT_FOUND:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    if result is catalog_crud.DeleteResult.IN_USE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El ejercicio está en una rutina; quítalo de la rutina antes de borrarlo",
        )


async def _set_favorite(
    session: AsyncSession, user: User, exercise_id: uuid.UUID, *, favorite: bool
) -> None:
    if not await catalog_crud.exercise_visible(session, user.id, exercise_id):
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
    if not await catalog_crud.exercise_visible(session, current_user.id, exercise_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return await exercise_history.build_history(session, current_user.id, exercise_id, limit=limit)


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
    seed_order = {code: index for index, (code, _, _) in enumerate(MUSCLE_SEED)}
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


@router.get("/exercises/{exercise_id}/alternatives", response_model=list[AlternativeOut])
async def get_exercise_alternatives(
    exercise_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=30)] = 8,
) -> list[AlternativeOut]:
    """Ejercicios parecidos (músculos, tipo de fuerza y patrón) para sustituir."""
    result = await alternatives(session, current_user, exercise_id, limit=limit)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return result
