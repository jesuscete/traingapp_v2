# TraingApp v2

Aplicación web para deportistas multidisciplinares (gimnasio, boxeo, running, etc.) con entrada desestructurada de entrenamientos mediante **chat con IA**.

## Visión

- Chat que interpreta entrenamientos en lenguaje natural ("5x5 press banca 80kg", "clase de boxeo de 1h30m").
- Evaluación de carga, actualización de estadísticas y sugerencias de ajuste.
- Dashboard visual de progreso, estancamiento y volumen total.
- Sistema modular de prompts/características por disciplina deportiva.
- Arquitectura de microservicios limpia y escalable, lista para móvil.

## Documentación

| Documento | Contenido |
| :--- | :--- |
| [Arquitectura](docs/architecture/ARCHITECTURE.md) | Servicios, comunicación y flujos de alto nivel |
| [ADR](docs/architecture/ADR.md) | Decisiones de diseño registradas |
| [Hoja de ruta](docs/ROADMAP.md) | Fases y hitos |
| [Setup](docs/SETUP.md) | Requisitos y puesta en marcha |

## Estructura del monorepo

```
traingapp_v2/
├── docs/                    # Documentación de arquitectura
├── services/
│   ├── api-gateway/         # FastAPI — core de negocio + auth
│   ├── ai-parser/           # FastAPI — NLP/LLM, evaluación de carga
│   └── web/                 # Next.js — dashboard/chat UI
├── shared/
│   ├── contracts/           # DTOs/schemas compartidos (OpenAPI)
│   └── libs/                # Utilidades cross-servicio
└── infra/                   # Docker Compose, Dockerfiles, CI
```
