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

### M1 · Experiencia de gimnasio (RF-06), prioridad alta 🟢 FUNCIONAL (falta probarla en el móvil)
Rediseño completo del flujo de gym, mobile-first, sobre el dataset ya cargado.

**Backend (225 tests en verde, ruff y mypy sin errores, migraciones probadas en PostgreSQL de ida y vuelta):**
- [x] ADR-001 aplicado (`services/session_ingest.py`). `migrate_legacy_gym` ejecutado: 0 sesiones antiguas que migrar.
- [x] Catálogo: `imageUrls`, favoritos, historial, récords y progresión (`/catalog/exercises/{id}/history`).
- [x] Traducción al español: 873 ejercicios en `data/exercises_es.json`; 821 de 865 en BD (los 44 restantes son del catálogo propio, ya en español).
- [x] Idempotencia: `clientId` en `POST /sessions/gym` (un reintento devuelve 200 con la misma sesión).
- [x] Notas por ejercicio en rutinas (`routine_exercise.notes`).
- [x] Corregido: la sugerencia de peso usaba series de todos los usuarios.
- [x] `dev-up.ps1 -Lan` para usar la app desde el móvil.

**Frontend (tsc y `next build` correctos, probado por HTTP de punta a punta):**
- [x] `/ejercicios`: búsqueda sin tildes, filtros por músculo/equipo/categoría/favoritos, scroll infinito.
- [x] `/ejercicios/[id]`: animación de 2 frames, músculos, instrucciones, récords, gráfica de 1RM e historial.
- [x] `/entrenar`: estado local persistente, columna "Anterior", tipos de serie, temporizador de descanso con vibración y pitido, superseries, sustituir/mover, Wake Lock, resumen con récords y músculos.
- [x] Cola de envío sin red con reintentos idempotentes. Los rechazos definitivos se guardan en `traingapp_failed_workouts_v1` (no se pierden).
- [x] PWA (manifest + icono), `/entrenos/[id]` con contenido real para gym.
- [x] Corregido: los ids no eran UUID por http://IP (sin `crypto.randomUUID`), así que el entreno se perdía al enviarlo desde el móvil.

**Pendiente / limitaciones conocidas:**
- [ ] **Probarlo de verdad en el móvil en el gym** y recoger ajustes de UX.
- [ ] Por http://IP no hay Wake Lock (requiere HTTPS): la pantalla puede apagarse. Opción: HTTPS local (mkcert) en M1.x o M8.
- [ ] Editor de rutinas: rediseño (plantillas y carpetas, reordenar, editar notas en la UI).
- [ ] Ejercicios personalizados (requiere cambiar la unicidad de `normalized_name` por usuario).
- [ ] `/ejercicios` no está en la barra inferior (ya tiene 5 pestañas); se llega por avatar, Entrenar y Rutinas.
- [ ] Deportes no-gym: solo por chat (se resuelve en M3).
- [ ] *Después:* programas multisemana y progresión sugerida.

### M2 · IA fiable con Claude (RNF-03)
- [ ] Proveedor `claude_cli` en `ai-parser/app/llm/factory.py`: subproceso asíncrono `claude -p --output-format json --json-schema <schema> --model <m>`, con timeout y control de errores.
- [ ] Esquemas pydantic como fuente de verdad de la salida: eliminar la extracción por regex duplicada y añadir un reintento de reparación.
- [ ] Campo `source: llm|fallback` en las respuestas. Registrar los fallos en log en vez de ocultarlos con un `except` silencioso.
- [ ] Llamadas largas (review/plan) por la cola Redis existente, con polling o SSE. Timeouts unificados.
- [ ] Autenticación servicio a servicio en ai-parser. Datos de usuario delimitados en el prompt, sin override del system prompt.

### M3 · Registro multideporte y fatiga (RF-01, RF-02)
- [ ] Esquemas de métricas por deporte (pydantic discriminado sobre `details`): fuerza, resistencia, combate (rounds × duración; saco/sparring/manoplas/comba), escalada, genérico.
- [ ] Formulario web dinámico por disciplina y edición de sesiones.
- [ ] La fatiga usa las métricas reales de combate y resistencia. Completar `CARDIO_DISCIPLINES`.
- [ ] Endpoint de "explicación de la fatiga": qué sesiones cargan cada músculo.

### M4 · Deporte principal y agente (RF-03, RF-04, RF-08)
- [ ] Perfil de demandas por deporte (empezar por boxeo): cualidades, patrones, músculos y rangos de reps/intensidad.
- [ ] Analizador determinista del historial real frente a las demandas, para obtener carencias. Claude redacta y justifica, no calcula.
- [ ] Recomendador de sustituciones por similitud (músculos, patrón, equipo) y "aplicar cambio" con un clic. Mover `web/lib/routineReview.ts` al backend.
- [ ] Agente conversacional con herramientas sobre los datos del usuario, memoria y confirmación antes de escribir. Sustituye progresivamente a `chat/plan_session.py`.

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
M1: empieza por aplicar ADR-001 (gym canónico + migración de datos) y por servir las imágenes del catálogo.
