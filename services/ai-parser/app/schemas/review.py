from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class RoutineReviewRequest(BaseModel):
    routineName: str
    payload: list[dict[str, object]]


class Solapamiento(CamelModel):
    descripcion: str
    grupos: list[str] = []
    dias: list[str] = []


class RoutineReviewResponse(CamelModel):
    puntos_fuertes: list[str] = []
    solapamientos: list[Solapamiento] = []
    sugerencias: list[str] = []