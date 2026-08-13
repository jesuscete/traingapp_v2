from app.schemas.review import RoutineReviewResponse, Solapamiento


def _day_group_load(days: list[dict[str, object]]) -> dict[str, list[str]]:
    """grupo muscular -> lista de dias donde aparece (por item de la rutina)."""
    result: dict[str, list[str]] = {}
    for day in days:
        if not isinstance(day, dict):
            continue
        day_label = str(day.get("diaSemana") or day.get("dayOfWeek") or "?")
        for group in day.get("gruposMusculares", []):
            if not isinstance(group, str):
                continue
            result.setdefault(group, [])
            if day_label not in result[group]:
                result[group].append(day_label)
    return result


def _find_by_type(days: list[dict[str, object]], tipo: str) -> list[str]:
    return [
        str(day.get("nombre"))
        for day in days
        if isinstance(day, dict) and day.get("tipo") == tipo and day.get("nombre")
    ]


def stub_review(days: list[dict[str, object]]) -> RoutineReviewResponse:
    nombres = [
        str(day.get("nombre") or day.get("tipo") or "?")
        for day in days
        if isinstance(day, dict)
    ]
    gym = _find_by_type(days, "gimnasio")
    deportes = _find_by_type(days, "deporte")

    puntos: list[str] = []
    if gym:
        puntos.append(
            "La rutina programa "
            f"{len(gym)} ejercicio(s) de gimnasio con series y repeticiones "
            "definidas."
        )
    if deportes:
        puntos.append(
            "Incluye actividad de deporte "
            f"({', '.join(nombres[:3])}) que aporta trabajo cardiovascular "
            "y estimulo muscular complementario."
        )
    if not puntos:
        puntos.append(
            "La rutina todavia tiene poca carga definida; empieza anadiendo "
            "ejercicios o disciplinas."
        )

    solapamientos: list[Solapamiento] = []
    for group, dias in sorted(_day_group_load(days).items()):
        if len(dias) >= 2:
            solapamientos.append(
                Solapamiento(
                    descripcion=(
                        f"El grupo {group} se trabaja en mas de un dia de la "
                        f"semana ({', '.join(dias)}); revisa que exista "
                        "descanso suficiente entre sesiones."
                    ),
                    grupos=[group],
                    dias=dias,
                )
            )

    sugerencias: list[str] = []
    if deportes and gym:
        sugerencias.append(
            "Evita cargar los mismos grupos musculares el dia siguiente a la "
            "sesion de deporte; separa al menos 48h cuando haya solapamiento."
        )
    sugerencias.append(
        "Distribuye el volumen de cada grupo muscular de forma equilibrada a "
        "lo largo de la semana."
    )
    if not sugerencias:
        sugerencias.append(
            "Anade ejercicios variados para cubrir todos los grupos "
            "musculares."
        )

    return RoutineReviewResponse(
        puntosFuerte=puntos,
        solapamientos=solapamientos,
        sugerencias=sugerencias,
    )