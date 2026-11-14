"""Tarjetas del chat construidas con datos (sin IA): rutina, fatiga, comidas y ejercicios.

Cada constructor devuelve la tarjeta y una frase corta de plantilla para la burbuja.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics import fatigue as fatigue_analytics
from app.analytics.sport_analysis import GROUP_LABELS
from app.crud import catalog as catalog_crud
from app.crud import routine as routine_crud
from app.models import Routine, User
from app.schemas.agent import CardItemOut, CardSectionOut, ChatCardOut
from app.schemas.sport_analysis import AlternativeOut, RecommendationOut
from app.services import fatigue_engine, nutrition

DAY_NAMES = {
    1: "Lunes",
    2: "Martes",
    3: "Miércoles",
    4: "Jueves",
    5: "Viernes",
    6: "Sábado",
    7: "Domingo",
}
DAY_TYPE_LABELS = {"gimnasio": "Gimnasio", "deporte": "Deporte", "descanso": "Descanso"}
LEVEL_LABELS = {"ok": "bien", "warning": "cargado", "danger": "muy cargado"}
MEAL_LABELS = {
    "desayuno": "Desayuno",
    "media_manana": "Media mañana",
    "comida": "Comida",
    "merienda": "Merienda",
    "cena": "Cena",
}


def _plural(n: int, one: str, many: str) -> str:
    return f"{n} {one if n == 1 else many}"


async def exercise_names(session: AsyncSession, user_id: uuid.UUID) -> dict[uuid.UUID, str]:
    out: dict[uuid.UUID, str] = {}
    for row in await catalog_crud.list_visible(session, user_id):
        name_es = (row.details or {}).get("nameEs")
        out[row.id] = name_es if isinstance(name_es, str) and name_es else row.name
    return out


async def routine_card(
    session: AsyncSession, user: User, only_day: int | None = None
) -> tuple[ChatCardOut | None, str]:
    routine = await routine_crud.get_active_routine(session, user.id)
    if routine is None:
        return None, (
            "No tienes una rutina activa. Puedes crear una en «Entrenar → Rutinas» o pedirme "
            "«crea una rutina» y te la monto paso a paso."
        )
    names = await exercise_names(session, user.id)
    disciplines = {d.id: d.name for d in await routine_crud.list_disciplines(session)}
    card = _routine_to_card(routine, names, disciplines, only_day)
    if only_day is not None:
        day = next((d for d in routine.days if d.day_of_week == only_day), None)
        if day is None or day.day_type == "descanso":
            return card, f"El {DAY_NAMES[only_day].lower()} es día de descanso en «{routine.name}»."
        if day.day_type == "deporte":
            sport = (
                disciplines.get(day.discipline_id, "deporte") if day.discipline_id else "deporte"
            )
            return card, f"El {DAY_NAMES[only_day].lower()} toca {sport.lower()}."
        return card, (
            f"El {DAY_NAMES[only_day].lower()} toca {day.label or 'gimnasio'}: "
            f"{_plural(len(day.exercises), 'ejercicio', 'ejercicios')}."
        )
    gym = sum(1 for d in routine.days if d.day_type == "gimnasio")
    return (
        card,
        f"Tu rutina activa es «{routine.name}», con {_plural(gym, 'día', 'días')} de gimnasio.",
    )


def _routine_to_card(
    routine: Routine,
    names: dict[uuid.UUID, str],
    disciplines: dict[uuid.UUID, str],
    only_day: int | None,
) -> ChatCardOut:
    sections: list[CardSectionOut] = []
    for day in sorted(routine.days, key=lambda d: d.day_of_week):
        if only_day is not None and day.day_of_week != only_day:
            continue
        kind = DAY_TYPE_LABELS.get(day.day_type, day.day_type)
        title = f"{DAY_NAMES[day.day_of_week]} · {day.label or kind}"
        items: list[CardItemOut] = []
        if day.day_type == "gimnasio":
            for ex in day.exercises:
                first = ex.sets[0] if ex.sets else None
                reps = (
                    f"{first.target_reps_min}-{first.target_reps_max}"
                    if first
                    and first.target_reps_max
                    and first.target_reps_max != first.target_reps_min
                    else str(first.target_reps_min)
                    if first and first.target_reps_min
                    else "—"
                )
                rest = (
                    f" · descanso {_rest(first.target_rest_seconds)}"
                    if first and first.target_rest_seconds
                    else ""
                )
                items.append(
                    CardItemOut(
                        title=names.get(ex.exercise_id, "Ejercicio"),
                        subtitle=f"{len(ex.sets)} × {reps}{rest}",
                        exercise_id=ex.exercise_id,
                    )
                )
        elif day.day_type == "deporte":
            sport = (
                disciplines.get(day.discipline_id, "Deporte") if day.discipline_id else "Deporte"
            )
            minutes = f"{day.target_duration_min} min" if day.target_duration_min else None
            items.append(CardItemOut(title=sport, subtitle=minutes))
        sections.append(CardSectionOut(title=title, items=items))
    return ChatCardOut(
        type="routine",
        title=routine.name,
        subtitle=DAY_NAMES[only_day] if only_day else "Semana",
        sections=sections,
        link="/entrenar?tab=rutinas",
        link_label="Abrir rutina",
    )


async def fatigue_card(session: AsyncSession, user: User) -> tuple[ChatCardOut, str]:
    fatigue = await fatigue_engine.simulate_fatigue(session, user.id)
    current = fatigue.states.get(fatigue.today, {})
    ranked = sorted(current.items(), key=lambda kv: kv[1], reverse=True)
    items = [
        CardItemOut(
            title=GROUP_LABELS.get(group, group).capitalize(),
            subtitle=f"{value:.0f}/100",
            badge=LEVEL_LABELS[fatigue_analytics.fatigue_level(value)],
            value=round(value, 1),
        )
        for group, value in ranked
        if value >= 1 or group in dict(ranked[:3])
    ]
    card = ChatCardOut(
        type="fatigue",
        title="Fatiga muscular",
        subtitle="0-100 · aviso desde 70, peligro desde 85",
        sections=[CardSectionOut(items=items)],
        link="/progreso?tab=fatiga",
        link_label="Ver detalle",
    )
    return card, fatigue_advice(ranked)


def fatigue_advice(ranked: list[tuple[str, float]]) -> str:
    """Frase accionable: los grupos más cargados con su cifra y qué hacer hoy."""
    top = [(g, v) for g, v in ranked[:3] if v >= 1]
    figures = ", ".join(f"{GROUP_LABELS.get(g, g)} {v:.0f}" for g, v in top)
    loaded = [g for g, v in ranked if v >= fatigue_analytics.WARN_LEVEL]
    legs = {"quadriceps", "hamstrings", "glutes", "calves"}
    if loaded:
        names = ", ".join(GROUP_LABELS.get(g, g) for g in loaded[:3])
        legs_loaded = bool(legs & set(loaded))
        return (
            f"Ojo: {names} por encima del aviso (70). Más cargado: {figures}. Hoy entrena otros "
            "grupos o haz técnica suave"
            + (
                " y deja las series de calidad o la pierna pesada para otro día."
                if legs_loaded
                else "."
            )
        )
    if not top or top[0][1] < 20:
        return (
            "Estás fresco: todos los grupos por debajo de 20/100 (aviso desde 70). Buen día para "
            "una sesión exigente o de calidad."
        )
    upper = [g for g, _ in top if g not in legs]
    leg_top = [g for g, _ in top if g in legs]
    hint = (
        " Si hoy toca pierna pesada, baja un poco el volumen; el tren superior está más fresco."
        if leg_top and not upper
        else " Si hoy toca tren superior, baja un poco el volumen; las piernas están más frescas."
        if upper and not leg_top
        else ""
    )
    return f"Vas bien: lo más cargado es {figures} (sobre 100; aviso desde 70).{hint}"


async def nutrition_card(session: AsyncSession, user: User) -> tuple[ChatCardOut, str]:
    day = await nutrition.day_summary(session, user, datetime.now(UTC).date())
    totals, target = day.totals, day.target
    items = [
        CardItemOut(
            title="Calorías",
            subtitle=f"{totals.kcal:.0f}"
            + (f" / {target.target_kcal:.0f} kcal" if target else " kcal"),
            value=min(100.0, totals.kcal / target.target_kcal * 100)
            if target and target.target_kcal
            else None,
        ),
        CardItemOut(
            title="Proteína",
            subtitle=f"{totals.protein_g:.0f}"
            + (f" / {target.protein_g:.0f} g" if target else " g"),
            value=min(100.0, totals.protein_g / target.protein_g * 100)
            if target and target.protein_g
            else None,
        ),
        CardItemOut(title="Hidratos", subtitle=f"{totals.carbs_g:.0f} g"),
        CardItemOut(title="Grasa", subtitle=f"{totals.fat_g:.0f} g"),
    ]
    meals = [
        CardItemOut(
            title=MEAL_LABELS.get(meal, meal),
            subtitle=", ".join(e.name for e in entries[:4]) + ("…" if len(entries) > 4 else ""),
            badge=f"{sum(e.kcal for e in entries):.0f} kcal",
        )
        for meal, entries in day.meals.items()
        if entries
    ]
    card = ChatCardOut(
        type="nutrition",
        title="Hoy",
        sections=[CardSectionOut(items=items), CardSectionOut(title="Comidas", items=meals)],
        link="/comidas",
        link_label="Abrir comidas",
    )
    if target is None:
        return card, f"Llevas {totals.kcal:.0f} kcal hoy. Completa tu perfil para ver tu objetivo."
    left = target.target_kcal - totals.kcal
    protein_left = target.protein_g - totals.protein_g
    if left > 0:
        return card, (
            f"Llevas {totals.kcal:.0f} de {target.target_kcal:.0f} kcal: te quedan {left:.0f} kcal"
            + (f" y {protein_left:.0f} g de proteína." if protein_left > 0 else ".")
        )
    return card, f"Ya has llegado a tu objetivo de hoy ({totals.kcal:.0f} kcal)."


def _rest(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} s"
    minutes = seconds / 60
    return f"{minutes:g} min" if minutes == int(minutes) else f"{minutes:.1f} min"


def recommendation_card(rec: RecommendationOut) -> tuple[ChatCardOut, str]:
    items = [
        CardItemOut(
            title=i.name,
            subtitle=f"{i.sets} × {i.reps_min}-{i.reps_max} · descanso {_rest(i.rest_seconds)}",
            badge=i.equipment_label,
            detail=i.reason + (f". {i.note.capitalize()}" if i.note else ""),
            image_url=i.image_url,
            exercise_id=i.exercise_id,
        )
        for i in rec.items
    ]
    card = ChatCardOut(
        type="exercises",
        title=rec.goal_label,
        subtitle=rec.sport_label,
        sections=[CardSectionOut(items=items)],
    )
    return (
        card,
        rec.summary + " Si te falta algún material, dime «no tengo …» y te doy alternativas.",
    )


def alternatives_card(
    groups: list[tuple[str, str | None, list[AlternativeOut]]],
) -> tuple[ChatCardOut, str]:
    """groups: (ejercicio origen, material que falta, alternativas)."""
    sections = [
        CardSectionOut(
            title=f"En vez de {source}" + (f" (sin {missing.lower()})" if missing else ""),
            items=[
                CardItemOut(
                    title=a.name,
                    badge=a.equipment_label,
                    detail=a.reason,
                    image_url=a.image_url,
                    exercise_id=a.exercise_id,
                )
                for a in alternatives
            ],
        )
        for source, missing, alternatives in groups
    ]
    card = ChatCardOut(type="exercises", title="Alternativas", sections=sections)
    first = groups[0][2][0].name if groups and groups[0][2] else None
    reply = (
        f"Te propongo opciones que trabajan lo mismo con otro material; la más parecida es {first}."
        if first
        else "No he encontrado alternativas con tu material."
    )
    return card, reply
