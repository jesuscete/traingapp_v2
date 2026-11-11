# ADR-003 · Llamadas LLM síncronas con timeout acotado (sin cola)

**Estado:** Aceptada · 2026-11-12 · Hito M2

## Problema
El roadmap preveía pasar las llamadas largas (revisión de rutina y generación de plan) a la cola Redis, con polling o SSE. Esas llamadas tardaban hasta 600 s con un modelo local de 3B en CPU y el gateway devolvía 502 por timeout.

## Decisión
Se mantienen síncronas con timeouts coherentes:
- ai-parser: 90 s por llamada al LLM (`APP_LLM_TIMEOUT_SECONDS`).
- gateway → ai-parser: 200 s (`APP_AI_PARSER_TIMEOUT_SECONDS`), que cubre la llamada y un reintento de reparación.

Con Claude (ADR-002) las respuestas miden 5 s (parseo) y 20 s (revisión de rutina). Las peticiones son asíncronas (httpx/asyncio), así que no bloquean el servidor.

## Consecuencias
- ✅ Sin infraestructura nueva ni cambios en el frontend.
- ⚠️ Si se vuelve a un modelo local lento o se añade una tarea de minutos (p. ej. un plan de varias semanas), hay que retomar la cola (el worker Redis ya existe para el chat).
