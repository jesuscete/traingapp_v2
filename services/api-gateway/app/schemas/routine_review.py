from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class RoutineReviewIn(BaseModel):
    routineName: str
    days: list[dict[str, object]]


class SolapamientoOut(CamelModel):
    descripcion: str
    grupos: list[str] = []
    dias: list[str] = []


class RoutineReviewOut(CamelModel):
    puntos_fuertes: list[str] = []
    solapamientos: list[SolapamientoOut] = []
    sugerencias: list[str] = []