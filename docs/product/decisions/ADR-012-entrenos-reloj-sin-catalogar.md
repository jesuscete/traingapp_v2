# ADR-012 · Entrenos del reloj sin catalogar

Fecha: 2026-11-14 · Estado: aceptado (pendiente de validar con Garmin real)

## Problema
Boxeo, fútbol, HYROX o CrossFit se graban en el reloj en modo «Cardio» / «Entreno». Garmin los manda como `training/cardio_training`, `hiit`… y la importación los guardaba como `other`. Con eso, la fatiga y el análisis usaban una carga genérica, aunque el reloj aporta FC, zonas, TRIMP y kcal reales.

## Decisión
- **Al importar** (archivo o Garmin): si la disciplina queda en `other`, se marca `details.classification = {status: "pending"}`. Solo afecta a las sesiones nuevas; las antiguas no tienen la marca y nunca se preguntan.
- **Kcal del reloj protegidas:** se guardan en `details.watchKcal`. Ninguna edición posterior las recalcula; antes, `PUT /sessions/{id}` las pisaba con la estimación por MET.
- **Endpoints:**
  - `GET /sessions/unclassified`: pendientes de los últimos 60 días.
  - `POST /sessions/classify/preview`: la IA interpreta la descripción y no guarda nada.
  - `POST /sessions/{id}/classify`: guarda la disciplina, una nota, el RPE, las métricas (p. ej. el WOD) y los ejercicios. Pasa a `done`.
  - `POST /sessions/{id}/classify/skip`: pasa a `skipped`.
- **Al catalogar** cambian la disciplina y `raw_text`. La FC, las zonas, el TRIMP, las kcal y el stream se conservan. La fatiga se recalcula con la carga muscular del deporte elegido y, si los hay, con los movimientos del WOD.
- **No catalogar:** el usuario puede negarse. La app avisa de que el análisis será menos preciso y no vuelve a preguntar por ese entreno. Desde el detalle se puede catalogar igualmente más tarde.
- **UI:**
  - "Hoy" muestra el aviso «Tienes N entrenos del reloj sin catalogar» y abre una hoja que los recorre uno a uno.
  - En la hoja: chips de deporte con icono, "Otra actividad…", descripción opcional con «Interpretar con IA», RPE y "No catalogar" con confirmación.
- Solo se pueden catalogar sesiones importadas (`external_source`). Las de fuerza del reloj ya llegan como gimnasio y no se recatalogan.

## Consecuencias
- Un entreno de HYROX con el reloj suma sus datos reales de FC y kcal al reparto muscular del HYROX. Lo mismo vale para boxeo, fútbol, etc.
- No hay migración: el estado vive en `details` (JSON).
- La IA es opcional: sin ella se cataloga con los chips y la descripción se guarda como nota.
- Pendiente: validar los `sport`/`subSport` reales de Garmin para otros modos (HIIT, «Otro»). Si alguno llega con una disciplina concreta pero equivocada, no se marcaría como pendiente.
