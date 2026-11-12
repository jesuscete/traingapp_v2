# ADR-007 · Importación de actividades de reloj (FIT/GPX/TCX)

**Estado:** Aceptada · 2026-11-12 · Hito M6.1

## Decisión
- **Fuente = el reloj**, no Strava (su API Policy 2026 prohíbe usar sus datos con IA y guardarlos más de 7 días; ver ANALISIS_TECNICO §7).
- **Formato común** (`analytics/activity_file.py`):
  - FIT con `fitdecode` (añadida como dependencia).
  - GPX y TCX con la librería estándar de XML.
  - Se extrae el resumen, las muestras (FC, velocidad, altitud, cadencia, potencia, distancia), las vueltas y las **series de fuerza** de Garmin.
- **Deporte del reloj → disciplina** (running, cycling, swimming, boxing, climbing…). La fuerza va al modelo de gym (ADR-001). Un GPX sin tipo se deduce por la velocidad.
- **FC** (`analytics/heart_rate.py`):
  - FC máxima de tu perfil o estimada con Tanaka (208 − 0,7·edad); FC en reposo de tu perfil o 60 por defecto.
  - **Zonas Karvonen** (50/60/70/80/90 % de la reserva) con el tiempo en cada zona, y **TRIMP de Banister**.
  - Si una actividad supera tu FC máxima, la app propone actualizarla.
- **Kcal:** primero las del reloj (Garmin usa Firstbeat), luego **Keytel por FC** y, si no hay nada, la estimación existente.
- **Fatiga:** si hay TRIMP, la carga sale de él (ya incluye la intensidad); referencia TRIMP 100 = volumen relativo 1.
- **Deduplicación:** `external_source='file'` + `external_id` (huella del archivo). Si hay una sesión del mismo deporte a esa hora (±10 min), devuelve `overlap` y solo importa con `force=true`.
- **Series temporales** en la tabla `activity_stream` (como máximo 1.500 puntos por actividad).
- **Subida:** el archivo va como cuerpo binario (`POST /activities/import?filename=`), uno por petición, máximo 15 MB. Así se evita la dependencia `python-multipart`.

## Consecuencias
- ✅ Funciona con cualquier reloj o app que exporte FIT, GPX o TCX, sin depender de terceros.
- ✅ Prepara M6.2: la API de Garmin entrega archivos FIT, así que se reutiliza el mismo lector.
- ⚠️ `fitdecode` se instaló con `pip` porque `uv` no está en este equipo. `pyproject.toml` está actualizado, pero `uv.lock` no: hay que ejecutar `uv lock` cuando `uv` esté disponible.
- ⚠️ Los tests usan FIT generados (`tests/fit_builder.py`). Falta validarlo con un archivo real de tu Garmin (M5.1).
