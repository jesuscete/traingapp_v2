# Plan de arreglos (roadmap)

> Plan propio, derivado del análisis del código ([GAP_ANALYSIS.md](GAP_ANALYSIS.md)). **No** se basa en los planes ni ADRs previos de OpenCode (`docs/architecture/*`). Cada hito se divide en micro-iteraciones que se aprueban antes de ejecutarlas (AGENTS.md §4). Al cerrar un hito, actualizar [requirements.yaml](requirements.yaml).

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

### M5 · Nutrición (RF-05)
- [ ] Decisión sobre la API de alimentos (FatSecret, Open Food Facts o Edamam: coste, cobertura en España, licencia).
- [ ] Modelo de ingesta, cliente con caché, búsqueda y entrada por texto libre vía el agente.
- [ ] Balance de ingesta frente a gasto (`kcal.py`) en el dashboard.

### M6 · Strava / Garmin (RF-07)
- [ ] OAuth con Strava y tokens cifrados con refresh.
- [ ] Webhook, importación y mapeo a los esquemas de M3, deduplicación e histórico.
- [ ] Garmin: evaluar la Health API (requiere ser partner) o usar el puente vía Strava.

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

## Dependencias

```
M0 ─► M1 (gym) ─► M3 ─► M6
  └─► M2 (IA) ─► M4 ─► M5
M1..M6 ─► M7 ─► M8
```
M1 solo usa el LLM para traducir las instrucciones (un lote único). Si M2 no está listo, se hace con el CLI a mano.

## Siguiente paso
Prueba real de M1–M4 en el móvil. Después, M5 (nutrición) o M6 (Strava), que son independientes.
