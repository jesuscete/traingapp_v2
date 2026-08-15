# TraingApp v2

Aplicación web para **deportistas multidisciplinares** (gimnasio, boxeo, running, ciclismo, etc.) que concilian distintos tipos de entrenamiento. El pilar principal es la **entrada desestructurada mediante chat con IA**: el usuario describe su sesión en lenguaje natural ("5x5 press banca 80kg" o "clase de boxeo de 1h30m"), el sistema la interpreta, evalúa la carga, actualiza estadísticas y sugiere ajustes.

## Stack

| Capa | Tecnología |
| :--- | :--- |
| Core backend (`api-gateway`) | Python 3.12+ · FastAPI · SQLAlchemy 2 (async) · Alembic |
| Servicio de IA / parsing (`ai-parser`) | Python 3.12+ · FastAPI · worker con cola Redis |
| Persistencia | PostgreSQL 16 (fuente de verdad) · Redis (colas/caché/sesión en vivo) |
| Frontend / dashboard (`web`) | Next.js 16 (Turbopack) · React 19 · TypeScript strict |
| Infraestructura | Docker Compose · GitHub Actions (CI) |
| Contratos compartidos | JSON Schema (`shared/contracts`) |

## Arquitectura

Microservicios con comunicación síncrona REST (OpenAPI) y asíncrona por cola Redis:

```
Web UI (Next.js :3000) ──► api-gateway (FastAPI :8000) ──► ai-parser (:8100, parsing/plan/review)
                                 │                            ▲
                                 ▼                            │
                           PostgreSQL ◄─────────────────────┘
                                 │
                              Redis (:6379)
                        ├── workout:parse (cola)         ──► worker ai-parser ──► POST /internal/sessions
                        ├── live:session (sesión en vivo)
                        ├── chat:draft (borradores TTL)
                        └── plan:session (flujo de plan)
```

Flujos principales:
1. **Chat → sesión** — `POST /chat/draft` (o `/chat/message` + worker) interpreta el texto y devuelve un `WorkoutDraft`; `POST /chat/confirm` lo persiste.
2. **Sesión en vivo** — `POST /live/start` abre una sesión en Redis (libre o desde una rutina); `POST /live/finish` persiste solo las series con peso.
3. **Rutinas** — CRUD de rutinas semanales (días gimnasio/deporte/descanso) y evaluación por IA (`POST /routines/review` → ai-parser).
4. **Plan por chat** — flujo conversacional que sugiere splits y genera un plan (`/chat/plan/*` → ai-parser `/plan/*`).
5. **Stats y fatiga** — análisis de carga, DOMS, readiness y fatiga muscular local por grupo con calibración personal.

## API (resumen)

| Método | Ruta | Auth | Descripción |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | — | Registro (devuelve JWT) |
| `POST` | `/auth/login` | — | Login (devuelve JWT) |
| `GET` / `PUT` | `/profile` | Bearer | Leer / actualizar perfil |
| `PUT` | `/profile/email` · `/profile/password` | Bearer | Cambiar email / contraseña |
| `POST` | `/sessions` | Bearer | Crear sesión estructurada |
| `GET` | `/sessions` | Bearer | Listar sesiones (paginado, filtro) |
| `GET` | `/sessions/summary` | Bearer | Resumen del periodo (historial) |
| `GET` / `DELETE` | `/sessions/{id}` | Bearer | Detalle / borrar sesión |
| `POST` / `GET` | `/sessions/gym` | Bearer | Crear / listar sesiones de gimnasio |
| `GET` | `/sessions/gym/{id}` | Bearer | Detalle de sesión de gimnasio |
| `POST` | `/chat/message` | Bearer | Encolar entrenamiento en lenguaje natural |
| `POST` | `/chat/draft` | Bearer | Parseo directo → borrador |
| `POST` | `/chat/confirm` · `/chat/cancel` | Bearer | Confirmar / cancelar borrador |
| `POST` | `/chat/plan/confirm` · `/chat/plan/cancel` | Bearer | Decisión sobre plan conversacional |
| `GET` / `POST` | `/live` | Bearer | Estado / cancelar sesión en vivo |
| `POST` | `/live/start` · `/live/finish` | Bearer | Abrir / cerrar sesión en vivo |
| `PATCH` | `/live/set` | Bearer | Actualizar serie en vivo |
| `POST` | `/live/exercises` · `/live/exercises/{i}/sets` | Bearer | Añadir ejercicio / serie en vivo |
| `GET` / `POST` | `/routines` | Bearer | Listar / crear rutinas |
| `GET` | `/routines/active` | Bearer | Rutina activa |
| `POST` | `/routines/review` | Bearer | Evaluación por IA de una rutina |
| `PUT` / `DELETE` | `/routines/{id}` | Bearer | Actualizar / borrar rutina |
| `PUT` / `DELETE` | `/routines/{id}/days/{dow}` | Bearer | Crear/actualizar / borrar día |
| `GET` | `/catalog/exercises` · `/disciplines` · `/muscles` · `/zones` | Bearer | Catálogo |
| `GET` / `POST` | `/stats/readiness` · `/stats/doms` · `/stats/calibration` | Bearer | Readiness, DOMS, calibración |
| `GET` | `/stats/energy` · `/fatigue` · `/fatigue/series` · `/load` · `/overview` · `/volume` · `/cardio` · `/progress` | Bearer | Estadísticas |
| `POST` | `/internal/sessions` | X-Internal-Token | Persistencia desde el worker |
| `POST` | `/parse` · `/plan/splits` · `/plan/generate` · `/analyze/routine` | — | Servicio ai-parser (directo) |

> Convención de nombres en la API: **camelCase** (alineada con el contrato JSON Schema de `shared/contracts`). Referencia detallada con payloads en [`docs/api/endpoints.md`](docs/api/endpoints.md).

## Puesta en marcha

### Requisitos previos

- Docker Desktop (PostgreSQL y Redis se levantan en contenedores).
- Python 3.12+ y [uv](https://docs.astral.sh/uv/) (`pip install uv`).
- Node.js 20+ para el frontend `web`. **En Windows este equipo: Node está en `E:\nodejs`** (fuera del PATH; usa `E:\nodejs\node.exe` y `E:\nodejs\npx.cmd`).

### Instalación

```bash
# 1. Dependencias de cada servicio
uv sync --project services/api-gateway
uv sync --project services/ai-parser
uv sync --project shared/contracts

# 2. Frontend
cd services/web && npm install
```

### Arranque (6 procesos)

> **Atajo (Windows):** `.\scripts\dev-up.ps1` arranca todo (infra Docker + migraciones + gateway, ai-parser, worker y web) y verifica la salud; `.\scripts\dev-down.ps1` detiene solo esos procesos. Detalle en [`docs/development/puesta-en-marcha.md`](docs/development/puesta-en-marcha.md).

```bash
# 1. Infraestructura (Postgres :5432 + Redis :6379)
make infra-up            # o: docker compose -f infra/docker-compose.yml up -d

# 2. Migraciones de base de datos
cd services/api-gateway && uv run alembic upgrade head

# 3. API Gateway (http://127.0.0.1:8000)
cd services/api-gateway && uv run uvicorn app.main:app --reload

# 4. API ai-parser (http://127.0.0.1:8100)
cd services/ai-parser && uv run uvicorn app.main:app --port 8100 --reload

# 5. Worker de parsing (otra terminal; solo para el flujo de /chat/message)
cd services/ai-parser && uv run python -m app.worker

# 6. Frontend (http://localhost:3000)
cd services/web && npx next dev
```

Configuración por variables de entorno (ver `services/*/.env.example`): `APP_DATABASE_URL`, `APP_REDIS_URL`, `APP_JWT_SECRET`, `APP_INTERNAL_TOKEN`, `APP_AI_PARSER_URL`, `APP_LLM_PROVIDER`, etc. Copia `.env.example` a `.env` para sobreescribir valores.

> Guía operativa verificada para Windows (con comandos PowerShell exactos): [`docs/development/puesta-en-marcha.md`](docs/development/puesta-en-marcha.md).

## Testing y calidad

```bash
make test    # pytest en contracts, api-gateway y ai-parser
make lint    # ruff + mypy en todos los servicios

# Frontend: verificación de tipos (no hay scripts de lint/test)
E:\nodejs\node.exe node_modules/typescript/bin/tsc --noEmit   # desde services/web
```

Tests: `api-gateway` (auth, sesiones, chat, token interno, stats), `ai-parser` (stub de parsing, plan, review), `shared/contracts` (validación JSON Schema). CI en GitHub Actions ejecuta lint + test + type-check por servicio.

## Git flow

- `master`: releases / código estable.
- `dev`: integración de desarrollo.
- `feature/*`: ramas de trabajo por funcionalidad (merge a `dev`).

## Estructura del repositorio

```
traingapp_v2/
├── .github/workflows/      # CI
├── infra/                  # docker-compose, Dockerfiles
├── docs/                   # arquitectura, setup, endpoints, troubleshooting
├── services/
│   ├── api-gateway/        # FastAPI — auth, sesiones, chat, rutinas, stats
│   ├── ai-parser/          # FastAPI — parsing NLP, plan, review + worker
│   └── web/                # Next.js 16 — dashboard, chat, rutinas, stats
├── shared/
│   └── contracts/          # JSON Schema compartidos
└── Makefile
```

## Hoja de ruta

- **F0** ✅ Fundación (infra, contratos, CI, esqueletos).
- **F1** ✅ MVP — backend completo (auth, sesiones, pipeline chat→parse→persistir) + dashboard web, rutinas, sesión en vivo, plan por chat.
- **F2** ◑ Estadísticas y tendencias, prompts por disciplina, fatiga y calibración (en desarrollo activo).
- **F3** Motor de sugerencias de carga.
- **F4** Escalado, PWA/móvil, observabilidad.
