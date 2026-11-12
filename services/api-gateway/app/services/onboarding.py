"""Qué le falta a un usuario nuevo para que la app funcione bien (determinista).

- `required`: datos sin los que fallan los cálculos (kcal, zonas, objetivo nutricional,
  preparación). Mientras falte alguno, la app muestra el formulario de bienvenida.
- `recommended`: pasos que mejoran la app (Garmin, metas, otros deportes); se pueden omitir.
"""

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import goals as goals_crud
from app.models import GarminConnection, User

RECOMMENDED_KEYS = ("secondary_sports", "garmin", "goal", "max_hr")


@dataclass(frozen=True)
class Step:
    key: str
    label: str
    done: bool
    skipped: bool = False
    href: str | None = None


def required_steps(user: User) -> list[Step]:
    return [
        Step("weight", "Peso", user.weight_kg is not None),
        Step("height", "Altura", user.height_cm is not None),
        Step("birth_date", "Fecha de nacimiento", user.birth_year is not None),
        Step("sex", "Sexo (para las kcal y las zonas)", user.sex is not None),
        Step("primary_sport", "Deporte principal", bool(user.primary_sport)),
    ]


async def recommended_steps(session: AsyncSession, user: User) -> list[Step]:
    skipped = set(user.onboarding_skipped or [])
    garmin = await session.get(GarminConnection, user.id)
    goals = await goals_crud.list_goals(session, user.id)
    secondary = [s for s in (user.sports or []) if s != user.primary_sport]
    steps = [
        Step("garmin", "Conecta tu Garmin", garmin is not None, href="/cuenta/conexiones"),
        Step(
            "goal", "Define tu objetivo", any(not g.done for g in goals), href="/cuenta/objetivos"
        ),
        Step(
            "secondary_sports",
            "Otros deportes que practicas",
            bool(secondary),
            href="/cuenta/objetivos",
        ),
        Step(
            "max_hr", "FC máxima (zonas precisas)", user.max_hr is not None, href="/cuenta/perfil"
        ),
    ]
    return [
        Step(s.key, s.label, s.done, skipped=s.key in skipped and not s.done, href=s.href)
        for s in steps
    ]
