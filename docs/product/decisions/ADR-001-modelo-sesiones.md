# ADR-001 · Modelo de sesiones: cabecera común + detalle por tipo

**Estado:** Aceptada · 2026-11-11 · Aplicada en M1 (fuerza → modelo gym) y M3 (métricas por deporte en `details.metrics`). Pendiente: retirar la tabla `exercises`, que conservan las sesiones no-gym antiguas

## Problema
Conviven dos formas de guardar el detalle de una sesión:

| | Legacy | Gym |
| :-- | :-- | :-- |
| Tablas | `exercises` (plana: nombre, series, reps, kg, duración, distancia) | `workout_exercise` → `set` → `set_entry` + `workout_session_summary` |
| Quién escribe | `POST /sessions` (también con `discipline=gym`), `/internal/sessions` (worker), confirmación de chat y fin de live **no-gym** | `POST /sessions/gym`, confirmación de chat **gym**, fin de live **gym** |
| Lectura | `GET /sessions/{id}` devuelve `GymSessionOut \| SessionOut` según qué relación tenga datos. La analítica aplana las dos (`computations.py:184`) | |

Una sesión de gym puede acabar en cualquiera de los dos modelos según por dónde entre. Por eso las respuestas son ambiguas y cada consumidor (stats, fatiga, kcal, web) tiene que contemplar ambos casos. M1 (experiencia de gym) necesita un único modelo fiable para series, récords e historial.

## Decisión
1. **`training_sessions` sigue siendo la cabecera universal** de cualquier actividad (fecha, duración, RPE, kcal, cardio, `details`). Encaja con RF-01.
2. **La fuerza solo se guarda en `workout_exercise/set/set_entry`.** Es el modelo canónico para M1: tipos de serie, superseries, entradas por lado y RPE por serie.
3. **La tabla `exercises` queda congelada:**
   - **M1:** `POST /sessions`, `/internal/sessions` y el chat convierten los ejercicios de fuerza (o `discipline=gym`) al modelo gym. Una migración de datos pasa las filas gym de `exercises` a `workout_*` (una serie por cada `sets`, con `reps` y `weight_kg`).
   - **M3:** las métricas de otros deportes pasan a esquemas por deporte en `details` (combate: rounds × duración y tipo; resistencia: distancia, ritmo y FC; escalada: vías y grado). Después se migran las filas restantes de `exercises` y se elimina la tabla.
4. La respuesta de `GET /sessions/{id}` pasa a ser un único esquema con `strength` (opcional) + `metrics` por deporte, sin la unión de dos tipos.

## Consecuencias
- ✅ Un único camino para gym. Récords, historial por ejercicio y "lo que hiciste la última vez" (M1) se consultan sobre una sola estructura.
- ✅ Se simplifican analytics, stats y la web (desaparece la rama legacy).
- ⚠️ Hacen falta dos migraciones de datos (M1 y M3) con su test. El contrato de `/sessions` cambia para la web, que se adapta en el mismo hito.
- ⚠️ El worker de ai-parser (`/internal/sessions`) debe enviar los ejercicios de fuerza en un formato convertible: se revisa en M2.
