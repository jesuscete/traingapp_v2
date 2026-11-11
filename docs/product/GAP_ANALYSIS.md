# Análisis de brecha: requisitos frente a estado actual

> Revisado el 2026-11-11 sobre `feature/dashboard`, contrastando con el código (no con los docs previos). Requisitos en [REQUISITOS.md](REQUISITOS.md); estado legible por máquina en [requirements.yaml](requirements.yaml).

## Resumen ejecutivo

La base es mejor de lo que parece en **datos y analítica**: modelo de fatiga Banister real, 873 ejercicios, 22 disciplinas con MET y unos 250 tests en backend. Las carencias graves son de **producto y de IA**:

1. **La "IA de fondo" no es un agente.** El chat son máquinas de estado con regex. El LLM solo se usa en endpoints sin estado. El proveedor por defecto es `stub` (sin LLM) y el modelo es local de 3B. La validación es débil y los fallos se ocultan en silencio.
2. **Faltan dos pilares enteros:** nutrición (RF-05) y Strava/Garmin (RF-07).
3. **El registro y el planificador están sesgados a gimnasio.** Para otros deportes no hay ni formulario ni métricas propias. El planificador es semanal fijo: sin calendario, sin programas y sin progresión.
4. **La seguridad es de prototipo** y bloquea el paso a móvil.

## Matriz de cobertura

| Req | Estado | Qué hay | Brecha principal |
| :-- | :-- | :-- | :-- |
| RF-01 Registro multideporte | 🟡 Parcial | `training_sessions.discipline` libre, 22 disciplinas, campos cardio, `details` JSONB, texto libre vía chat, modo live gym | `details` sin esquema por deporte, la web solo tiene formulario de gym, no se pueden editar sesiones |
| RF-02 Fatiga | 🟢 Sólido / 🟡 | `analytics/fatigue.py` (impulso-respuesta, ACWR, DOMS, calibración) y mapa corporal | Entradas no-gym estimadas (golpes/min inventados), falta explicar el origen de la fatiga, parámetros hardcodeados |
| RF-03 Adaptar a deporte | 🔴 Stub | `chat/plan_session.py` (1038 líneas, regex), prompts por disciplina | No hay modelo de demandas por deporte (boxeo: potencia rotacional, resistencia de hombro, cuello, core anti-rotación…) ni justificación |
| RF-04 Análisis y recomendador | 🟡 Básico | `/routines/review` llama al LLM, fallback en `web/lib/routineReview.ts` | Analiza la rutina declarada, no el historial; no hay recomendador de sustituciones; lógica duplicada en el frontend |
| RF-05 Nutrición | 🔴 Ausente | Solo gasto (`analytics/kcal.py`) | Todo |
| RF-06 Biblioteca y planificador | 🟡 Básico | 873 ejercicios free-exercise-db, rutina semanal, sesión live, stats de progreso | Imágenes, ejercicios propios, calendario, programas multisemana, progresión/PRs; `/entrenos/[id]` tiene placeholders |
| RF-07 Strava/Garmin | 🔴 Ausente | Campos cardio y `/internal/sessions` | Todo |
| RF-08 Chatbot | 🔴 Stub | Borrador/confirmación de sesión y plan guiado (Redis) | Agente con tool use, memoria y consultas libres ("¿cómo voy de piernas?") |

## Hallazgos técnicos transversales

### IA (RNF-03)
- `APP_LLM_PROVIDER=stub` por defecto. Proveedores disponibles: Ollama u OpenAI-compatible. No hay Claude.
- El JSON se extrae con regex `\{.*\}` y se coerciona a mano. No hay esquema estricto ni reintento de reparación.
- El patrón `except Exception` devuelve el stub sin avisar: la respuesta no indica que no vino del LLM.
- Timeouts incoherentes: ai-parser 30 s (600 s en `.env.example`), gateway 60/120/360/600 s, todos en peticiones **síncronas**.
- No hay defensa frente a prompt injection. El gateway puede sobrescribir el `systemPrompt`.

### Seguridad (RNF-01)
- Secretos por defecto en código (`jwt_secret`, `internal_token`, credenciales de DB) sin bloqueo en producción.
- [internal.py:20](../../services/api-gateway/app/api/internal.py#L20) compara el token con `!=` en vez de `hmac.compare_digest`.
- [deps.py:33](../../services/api-gateway/app/api/deps.py#L33): `uuid.UUID(subject)` sin control, así que un `sub` malformado devuelve 500 en vez de 401.
- ai-parser no tiene autenticación de entrada.
- No hay rate limiting, refresh tokens, recuperación de contraseña ni verificación de email.
- La web guarda el JWT en `localStorage` y repite la guarda de auth en cada página.
- La autorización por recurso (`/sessions/{id}`, `/routines/{id}`) está **pendiente de verificar endpoint a endpoint**.

### API y móvil (RNF-02)
- No hay versionado. CORS está hardcodeado a `localhost:3000` en [main.py:14](../../services/api-gateway/app/main.py#L14).
- [web/lib/types.ts](../../services/web/lib/types.ts) (554 líneas) está escrito a mano y no se genera desde OpenAPI, así que puede desincronizarse.
- No hay PWA ni i18n.

### Arquitectura y calidad (RNF-04)
- No hay capa de servicios: `api/stats.py` (624 líneas) y `chat/plan_session.py` (1038) mezclan HTTP, dominio y estado.
- Conviven el modelo legacy (`training_sessions`/`exercises`) y el de gym (`workout_exercise`/`set`), con respuestas `GymSessionOut | SessionOut`.
- `kcal.CARDIO_DISCIPLINES` solo incluye 5 de las 22 disciplinas.
- La web no tiene tests ni script de test.
- Los contratos de `shared/contracts` no se validan contra los esquemas pydantic.

## Qué conservar
- `analytics/` (fatiga, kcal, carga, calibración): es el activo más valioso. Hay que extenderlo, no reescribirlo.
- El catálogo free-exercise-db y su seed.
- La batería de tests del gateway y el flujo borrador → confirmación (útil como patrón de confirmación en el agente).
- Los componentes visuales: BodyMap y los gráficos SVG.
