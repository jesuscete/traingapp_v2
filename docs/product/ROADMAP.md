# Plan de arreglos (roadmap)

> Plan propio, derivado del análisis del código ([GAP_ANALYSIS.md](GAP_ANALYSIS.md)). **No** se basa en los planes ni ADRs previos de OpenCode (`docs/architecture/*`). Cada hito se divide en micro-iteraciones que se aprueban antes de ejecutarlas (AGENTS.md §4). Al cerrar un hito, actualizar [requirements.yaml](requirements.yaml).

## 📍 Estado actual (2026-11-12)

| Hito | Estado |
| :-- | :-- |
| M0 Saneamiento | ✅ |
| M1 Gimnasio | ✅ (falta probarlo en el móvil) |
| M2 IA con Claude | ✅ |
| M3 Multideporte y fatiga | ✅ |
| M4 Deporte principal y agente | ✅ |
| M4.1 Mejoras encontradas | ✅ fatiga, 1RM y registro de deporte |
| **M5 Nutrición** | ⏳ **Siguiente** |
| M5.1 Prueba en el móvil en local y depuración | ⏳ |
| M6 Garmin (antes "Strava/Garmin") | ⏳ |
| M7 Blindaje | 🟡 parcial |
| M8 App móvil | 🟡 parcial (PWA, `-Lan`, `-Https`) |

- **Código:** todo en `feature/refactor` (último commit `eefde7f`). Pasan los tests del gateway (254) y de ai-parser (64); `ruff`, `mypy` y `tsc` sin errores.
- **Pendiente tuyo:**
  - Probar M1-M4 en el móvil.
  - Instalar mkcert para `-Https`.
  - Hacer merge de tus cambios locales en `fatiga/page.tsx`, `MuscleChart.tsx` y `routineReview.ts`.

## Principios de orden
1. **Usable cuanto antes en la vida real:** la experiencia de gimnasio (RF-06) va primero, porque el Arquitecto la usará a diario y eso genera datos reales para todo lo demás.
2. **IA fiable antes que funciones de IA:** el adaptador de Claude va antes del agente y del recomendador.
3. **Seguridad mínima ya** (bugs triviales en M0). El blindaje completo va antes de la app móvil nativa.

## Decisiones tomadas
- **LLM:** se usa Claude a través del CLI local `claude -p --json-schema` (suscripción de Claude Code) como un nuevo proveedor del `factory` existente de ai-parser. Ollama y stub se mantienen. Más adelante se podrá cambiar a la API de Anthropic (SDK `anthropic`) sin tocar los servicios. *Límite:* sirve para uso personal y local, no para varios usuarios ni producción (ahí hará falta una API key). Ver [ADR-002](decisions/ADR-002-proveedor-llm.md).

## Hitos

### M0 · Saneamiento ✅ (2026-11-11)
- [x] Un token con `sub` malformado devuelve 401 en vez de 500. `hmac.compare_digest` en `/internal`.
- [x] Con `APP_ENV=production` no se arranca si hay secretos por defecto (gateway y ai-parser). CORS configurable con `APP_CORS_ORIGINS`.
- [x] Tests de aislamiento entre usuarios en los endpoints `/{id}`: sin fugas. Las claves de Redis (live, plan, borradores) van ligadas al usuario.
- [x] Higiene: los logs de `dev-up.ps1` van a `logs/`, se borraron logs y caché obsoleta y hay un README real en web.
- [x] Modelo de sesiones: [ADR-001](decisions/ADR-001-modelo-sesiones.md). Proveedor LLM: [ADR-002](decisions/ADR-002-proveedor-llm.md).

### M1 · Experiencia de gimnasio (RF-06) ✅ (2026-11-12, falta probarla en el móvil)
- [x] ADR-001 aplicado; `migrate_legacy_gym` ejecutado (0 sesiones que migrar).
- [x] Biblioteca: imágenes, búsqueda sin tildes, filtros, favoritos, **ejercicios propios** (crear/borrar, aislados por usuario), ficha con récords, 1RM e historial.
- [x] Traducción al español (873 ejercicios). Los ejercicios se resuelven por `exerciseId` y por nombre en español (corregida la pérdida de historial y de impactos musculares).
- [x] Entreno en vivo: estado local persistente, "Anterior", tipos de serie, descanso con vibración, superseries, cola offline idempotente (`clientId`), resumen con récords.
- [x] Rutinas: duplicar (plantilla), reordenar, notas y superseries en el editor; las notas pasan al entreno. Validación de ejercicios ajenos o inexistentes (422).
- [x] PWA (manifest), `dev-up.ps1 -Lan` y `-Https` (mkcert) para instalarla de verdad en el móvil.
- [ ] Probar en el móvil en el gym y ajustar la UX.
- [ ] *Aplazado:* carpetas de rutinas, programas multisemana, progresión sugerida (al planificador de M4).

### M2 · IA fiable con Claude (RNF-03) ✅ (2026-11-12)
- [x] Proveedor `claude_cli` (ADR-002), activo en el `.env` local; Ollama y OpenAI se mantienen.
- [x] Salida estructurada nativa en los 3 proveedores + validación pydantic + 1 reintento de reparación (`llm/structured.py`). Eliminada la extracción por regex.
- [x] `source: llm|fallback` en todas las respuestas de ai-parser y en `/routines/review` (con indicador en la web). Solo se captura `LLMError`, y el fallo se registra en el log antes del fallback.
- [x] `X-Internal-Token` obligatorio en ai-parser; datos del usuario delimitados (`<datos_usuario>`). Probado: ignora la inyección de prompt y la anota.
- [x] Timeouts coherentes (90 s / 200 s). **Cambio:** sin cola, ver [ADR-003](decisions/ADR-003-llamadas-llm-sincronas.md).
- [x] Corregido: el prompt de revisión pedía `solapamientos` como texto y el código los descartaba todos.

### M3 · Registro multideporte y fatiga (RF-01, RF-02) ✅ (2026-11-12)
- [x] Métricas por deporte validadas (`schemas/metrics.py`, en `details.metrics`): combate (bloques saco/sparring/manoplas/comba/sombra/técnica/físico con rounds×duración o minutos), resistencia (distancia, FC, desnivel), escalada (estilo + vías con grado), genérica. Se rechazan las que no encajan con la disciplina (422).
- [x] La duración se deriva de los bloques; la distancia, la FC y el desnivel alimentan sus columnas y las kcal.
- [x] Fatiga: volumen de combate a partir de los bloques (golpes equivalentes por tipo), ciclismo y natación por km con pendiente, artes marciales como combate.
- [x] **Fix:** la fatiga y las kcal ignoraban `intensity` (las 30 sesiones de gym contaban con RPE 5). Ahora: `details.rpe` → `intensity` → RPE medio de las series.
- [x] `GET /stats/fatigue/explain?group=`: descomposición exacta de la fatiga actual por sesión.
- [x] `PUT /sessions/{id}`: edición parcial (en gym solo los datos generales).
- [x] IA: el parseo extrae bloques de combate y datos de resistencia, y el chat los guarda al confirmar (probado con Claude: 4,9 s).
- [x] Web: `/registrar` con formulario por deporte, detalle y edición de sesiones, explicación de la fatiga en el dashboard y métricas en el borrador del chat.
- [ ] *Aplazado:* retirar la tabla `exercises` (segunda parte del ADR-001); dividir una sesión mixta en varias.

### M4 · Deporte principal y agente (RF-03, RF-04, RF-08) ✅ (2026-11-12)
- [x] Perfil de demandas del boxeo (`analytics/sport_analysis.py`): patrones (rotación, anti-rotación, pliometría, explosivos, unilateral, bisagra, cuello, tirones), rangos de series por músculo, zonas de repeticiones, equilibrio tirón/empuje y conflictos con los días de deporte. Hay un perfil genérico para el resto de deportes.
- [x] Clasificación de patrones de movimiento por ejercicio (`analytics/patterns.py`).
- [x] `GET /analysis/sport`: análisis determinista del historial (≥3 sesiones en 4 semanas) o de la rutina activa, con puntuación, carencias y ejercicios sugeridos. Con `narrative=true`, Claude redacta el diagnóstico y las prioridades.
- [x] Recomendador: `GET /catalog/exercises/{id}/alternatives` (similitud muscular, de fuerza y de patrón) y aplicar con un clic (`POST /routines/{id}/exercises/{eid}/swap`, `POST /routines/{id}/days/{dow}/exercises`).
- [x] Agente conversacional con 10 herramientas, memoria y confirmación antes de escribir ([ADR-004](decisions/ADR-004-agente-conversacional.md)). Probado con Claude: 8-14 s por turno.
- [x] Motor de fatiga movido a `services/fatigue_engine.py` (lo comparten las estadísticas y el agente).
- [ ] *Aplazado:* mover `web/lib/routineReview.ts` al backend (es un fichero con cambios locales del Arquitecto); planes multisemana generados por el agente.

### M4.1 · Mejoras encontradas ✅ (2026-11-12, [ADR-005](decisions/ADR-005-fatiga-1rm-registro-deporte.md))
Origen: [ANALISIS_TECNICO.md](ANALISIS_TECNICO.md) §2, §3 y §5.
1. **Fatiga realista**
   - [x] Cada ejercicio y cada deporte carga sus músculos con su nivel de implicación (p. ej. dominadas: espalda > bíceps > antebrazo). La carga de gym sale de las **series reales** (activación × esfuerzo por serie).
   - [x] Recuperación en **dos compartimentos reales** (agudo y residual) con τ por grupo muscular, más prolongada en grupos grandes y excéntricos.
   - [x] Deportes: pesos musculares por tipo de bloque (comba, saco, sparring…).
2. **1RM único y fiable**
   - [x] Una sola fórmula en toda la app: tabla RPE→%1RM (RTS); sin RPE asume RPE 10; 1-12 reps. Backend `analytics/strength.py` y web `lib/strength.ts`, con los mismos vectores de prueba.
3. **Registro de conocimiento por deporte**
   - [x] Perfil estructurado por deporte (boxeo el primero): cualidades, patrones, ejercicios clave, series por músculo, zonas de reps por fase, lesiones y prehab, reglas de calendario y carga por bloque.
   - [x] La IA lo consulta (prompt compacto + herramienta `perfil_deporte`) en vez de deducirlo.

**Backlog de mejoras** (después de M5): progresión sugerida (doble progresión), kcal por FC (Keytel), retirar `chat/plan_session.py`, imágenes sin conexión, sesiones mixtas.

### M5 · Nutrición (RF-05) ⏳ siguiente
- [x] Decisión de la API (análisis §6): **Open Food Facts** (código de barras y marcas de España) + **USDA** (genéricos) + **Claude** para el texto libre. Caché local de lo consultado.
- [ ] **Modelo:** `food` (por 100 g + raciones típicas), `meal_entry` (copia de los macros y **método de registro**: pesada / etiqueta / rápida / estimada por IA), `meal_template` (mis platos), `body_weight_log`, `nutrition_goal`.
- [ ] **Cálculos:** Mifflin-St Jeor + actividad + kcal de los entrenos reales → objetivo diario. Macros: proteína 1,6-2,2 g/kg, grasa mínima ~0,8 g/kg, resto en hidratos. Balance diario y semanal.
- [ ] **Objetivos:** perder, mantener, ganar y **corte hacia una categoría de peso** (peso objetivo y fecha).
- [ ] **Dos formas de registrar:**
  - **Precisa (manual):** gramos exactos de báscula sobre un alimento; alimento propio con los valores de la etiqueta; añadido rápido de kcal y macros.
  - **Rápida (IA):** texto libre ("2 tostadas con crema de cacahuete") → propuesta de alimentos y gramos que el usuario ajusta y confirma.
  - Se muestra qué parte de las kcal del día es exacta y cuál estimada.
- [ ] Búsqueda (recientes y favoritos primero), **código de barras** (la cámara necesita `-Https`/mkcert en el móvil; si no, el código se teclea), mis platos.
- [ ] Agente: `registrar_comida` (propone, el usuario confirma) y `ver_nutricion`.
- [ ] Web: pantalla Comidas (anillos de kcal y macros por comida), añadir comida (4 vías), peso con tendencia, tarjeta de balance en el dashboard, objetivos en el perfil.
- Valores por defecto acordados: kcal + proteína + hidratos + grasa + fibra (azúcar si viene en el producto); comidas: desayuno, comida, merienda, cena y snack.

### M5.1 · Prueba en el móvil en local y depuración ⏳
- [ ] `dev-up.ps1 -Lan` / `-Https` en el móvil: registrar comidas y entrenos, chat, preparación, fatiga.
- [ ] Lista de errores y ajustes de UX; corregirlos antes de seguir.

### M6 · Garmin (RF-07)
- [x] Decisión (análisis §7): **Strava descartado de momento**, porque su acuerdo de API prohíbe usar sus datos en aplicaciones de IA y desde 2026 exige suscripción. **Garmin con clave personal + importación FIT.**
- [ ] `external_account` (tokens cifrados), `external_source` + `external_id` para deduplicar, ingesta por la cola Redis.
- [ ] Parser FIT (`fitdecode`) → disciplina + métricas de resistencia (FC, desnivel) → kcal y fatiga.
- [ ] Health Connect / HealthKit en la app nativa (M8).

### M7 · Blindaje (RNF-01, RNF-05)
- [ ] Token de acceso corto con refresh rotatorio y revocación. Cookie httpOnly en web.
- [ ] Rate limiting, bloqueo por intentos, verificación de email y recuperación de contraseña.
- [ ] Revisión OWASP API Top 10, cabeceras de seguridad y auditoría de dependencias en CI.
- [ ] RGPD: exportación y borrado de cuenta; minimizar los datos enviados al LLM.
- [ ] Proveedor LLM de producción (API key) si hay más usuarios.

### M8 · App móvil (RNF-02)
- [ ] Prefijo `/api/v1`, errores RFC 7807, paginación coherente.
- [ ] Tipos generados desde OpenAPI para web y móvil.
- [ ] App nativa (React Native/Expo reutilizaría TypeScript) frente a seguir con la PWA: decidir.

## 🗂️ Backlog (ideas para cuando la app esté en uso, después de M8)
Tu objetivo: que la IA te organice y te guíe sin tener que ser experto. Las mejoras saldrán de usar la app.

- **Completar los perfiles de deporte** (`data/sport_profiles/`): revisar el de boxeo con el uso real y añadir los deportes que practiques (running, escalada…). Proceso: Claude genera un borrador estructurado, se revisa y se valida automáticamente.
- **Feedback diario de recuperación para refinar la fatiga:**
  - "Hoy me noto descansado / sigo cansado" y las agujetas por músculo al día siguiente de entrenar.
  - Ya existe la base: readiness diaria, mapa corporal de agujetas (`daily_muscle_doms`) y calibración personal (`user_muscle_calibration`). Falta preguntarte de forma proactiva (por ejemplo, el agente o una notificación tras cada entreno) y usar tus respuestas para ajustar automáticamente las constantes de recuperación por músculo.
- **Fatiga que aprende:** comparar lo que predice el modelo con lo que reportas y corregir τ y pesos con el tiempo (ADR-005, consecuencias).
- **Fase de temporada y calendario de combate** en tu perfil, para que los objetivos cambien solos (precompetición, descarga).

## Dependencias

```
M0 ─► M1 (gym) ─► M3 ─► M6
  └─► M2 (IA) ─► M4 ─► M5
M4 ─► M4.1 (mejoras) ─► M5 (comidas) ─► M5.1 (prueba en el móvil) ─► M6 ─► M7 ─► M8
M1..M6 ─► M7 ─► M8
```
M1 solo usa el LLM para traducir las instrucciones (un lote único). Si M2 no está listo, se hace con el CLI a mano.

## Siguiente paso
**M5** comidas → **M5.1** prueba en el móvil en local → M6, M7, M8.
