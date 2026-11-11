# ADR-004 · Agente conversacional con herramientas sobre salida estructurada

**Estado:** Aceptada · 2026-11-12 · Hito M4

## Problema
RF-08 pide un chat flexible que consulte y modifique los datos del usuario. El chat anterior eran máquinas de estado con regex. El proveedor (Claude vía CLI, ADR-002) no expone tool use nativo, y los datos viven en el api-gateway, no en ai-parser.

## Decisión
- **Bucle en el gateway**, que tiene los datos: `services/agent.py` llama en cada paso a ai-parser `/agent/step`, que devuelve por salida estructurada `responder` o `herramienta` (nombre y argumentos). El gateway ejecuta la herramienta y le pasa el resultado. Máximo 4 herramientas por turno; en el quinto paso se fuerza la respuesta.
- **Herramientas** (`services/agent_tools.py`):
  - **Lectura:** fatiga, explicación de la fatiga, sesiones recientes, análisis de deporte, rutina, búsqueda de ejercicios y alternativas.
  - **Escritura:** registrar entreno, sustituir y añadir en la rutina. **Solo proponen**: crean una acción pendiente en Redis (TTL 1 h) que el usuario confirma con un botón.
- **Memoria:** conversación en Redis (24 h, últimos 30 mensajes; al LLM se envían los 16 últimos, incluidos los resultados de herramientas).
- **El LLM no calcula:** las cifras salen de las herramientas deterministas (análisis M4, fatiga M3).

## Consecuencias
- ✅ Funciona con cualquier proveedor (Claude CLI, Ollama, OpenAI) y no depende de tool use nativo.
- ✅ Nada se escribe sin confirmación explícita; los argumentos se validan en el gateway (ids visibles para el usuario, rangos).
- ⚠️ Latencia de 8-15 s por turno con 1-2 herramientas (un proceso de CLI por paso). Si molesta, se puede pasar a la API de Anthropic con tool use nativo y streaming (M7).
- ⚠️ El plan guiado antiguo (`chat/plan_session.py`) sigue disponible, pero se retirará cuando el agente genere planes completos.
