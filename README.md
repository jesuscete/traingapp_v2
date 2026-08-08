# TraingApp v2

Aplicación web para **deportistas multidisciplinares** (gimnasio, boxeo, running, ciclismo, etc.) que concilian distintos tipos de entrenamiento. El pilar principal es la **entrada desestructurada mediante chat con IA**: el usuario describe su sesión en lenguaje natural ("5x5 press banca 80kg" o "clase de boxeo de 1h30m"), el sistema la interpreta, evalúa la carga, actualiza estadísticas y sugiere ajustes.

## Stack

| Capa | Tecnología |
| :--- | :--- |
| Core backend (`api-gateway`) | Python 3.12+ · FastAPI · SQLAlchemy 2 (async) · Alembic |
| Servicio de IA / parsing (`ai-parser`) | Python 3.12+ · FastAPI · worker con cola Redis |
| Persistencia | PostgreSQL 16 (fuente de verdad) · Redis (colas/caché) |
| Frontend / dashboard (`web`) | Next.js 14+ (TypeScript strict) — *pendiente* |
| Infraestructura | Docker Compose · GitHub Actions (CI) |
| Contratos compartidos | JSON Schema (`shared/contracts`) |

## Arquitectura

Microservicios con comunicación síncrona REST (OpenAPI) y asíncrona por cola Redis:

```
Web UI (Next.js) ──► api-gateway (FastAPI) ──► Redis (workout:parse)
                        ▲        │                  │
                        │        ▼                  ▼
                   PostgreSQL   ◄──── ai-parser (worker) ──► POST /internal/sessions
```

Flujo principal:
1. `POST /chat/message` — el usuario envía texto en lenguaje natural; se encola en Redis (`202 Accepted`).
2. Worker de `ai-parser` consume la cola, interpreta con un parser (stub regex; LLM en roadmap) y genera un `WorkoutDraft`.
3. `POST /internal/sessions` (token interno) — `api-gateway` persiste la sesión y calcula el volumen (sets × reps × kg).
4. `GET /sessions` — el dashboard/usuario consulta el histórico.

## API (resumen)

| Método | Ruta | Auth | Descripción |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | — | Registro (devuelve JWT) |
| `POST` | `/auth/login` | — | Login (devuelve JWT) |
| `POST` | `/sessions` | Bearer | Crear sesión estructurada |
| `GET` | `/sessions` | Bearer | Listar sesiones del usuario |
| `GET` | `/sessions/{id}` | Bearer | Detalle de sesión |
| `DELETE` | `/sessions/{id}` | Bearer | Borrar sesión |
| `POST` | `/chat/message` | Bearer | Encolar entrenamiento en lenguaje natural |
| `POST` | `/parse` | — | Parser directo (ai-parser) |
| `POST` | `/internal/sessions` | X-Internal-Token | Persistencia desde el worker |

> Convención de nombres en la API: **camelCase** (alineada con el contrato JSON Schema de `shared/contracts`).

## Puesta en marcha

### Requisitos previos

- Docker Desktop (PostgreSQL y Redis se levantan en contenedores)
- Python 3.12+ y [uv](https://docs.astral.sh/uv/) (`pip install uv`)
- Node.js 20+ (solo para el frontend `web`, pendiente de implementar)

### Instalación y arranque

```bash
# 1. Dependencias de cada servicio
uv sync --project services/api-gateway
uv sync --project services/ai-parser
uv sync --project shared/contracts

# 2. Infraestructura (Postgres + Redis)
make infra-up            # o: docker compose -f infra/docker-compose.yml up -d

# 3. Migraciones de base de datos
cd services/api-gateway && uv run alembic upgrade head

# 4. API Gateway (http://127.0.0.1:8000)
cd services/api-gateway && uv run uvicorn app.main:app --reload

# 5. Worker de parsing (en otra terminal)
cd services/ai-parser && uv run python -m app.worker
```

Configuración por variables de entorno (ver `services/*/.env.example`): `APP_DATABASE_URL`, `APP_REDIS_URL`, `APP_JWT_SECRET`, `APP_INTERNAL_TOKEN`, etc. Copia `.env.example` a `.env` para sobreescribir valores.

## Testing y calidad

```bash
make test    # pytest en contracts, api-gateway y ai-parser
make lint    # ruff + mypy en todos los servicios
```

Tests: `api-gateway` (auth, sesiones, chat, token interno), `ai-parser` (stub de parsing), `shared/contracts` (validación JSON Schema). CI en GitHub Actions ejecuta lint + test + type-check por servicio.

## Git flow

- `master`: releases / código estable.
- `dev`: integración de desarrollo.
- `feature/*`: ramas de trabajo por funcionalidad (merge a `dev`).

## Estructura del repositorio

```
traingapp_v2/
├── .github/workflows/      # CI
├── infra/                  # docker-compose, Dockerfiles
├── services/
│   ├── api-gateway/        # FastAPI — auth, sesiones, chat, stats
│   ├── ai-parser/          # FastAPI — parsing NLP + worker
│   └── web/                # Next.js — dashboard (pendiente)
├── shared/
│   └── contracts/          # JSON Schema compartidos
└── Makefile
```

## Hoja de ruta

- **F0** ✅ Fundación (infra, contratos, CI, esqueletos).
- **F1** ◑ MVP — backend completo (auth, sesiones, pipeline chat→parse→persistir); pendiente dashboard web.
- **F2** Estadísticas y tendencias, prompts por disciplina.
- **F3** Motor de sugerencias de carga.
- **F4** Escalado, PWA/móvil, observabilidad.
