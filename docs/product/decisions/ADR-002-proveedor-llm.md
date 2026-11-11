# ADR-002 · Proveedor LLM: Claude vía CLI local

**Estado:** Aceptada · 2026-11-11 · Se implementa en M2

## Problema
ai-parser usa por defecto `stub` (sin LLM) o un modelo local de 3B (Ollama). La calidad no alcanza para analizar rutinas, adaptar a un deporte ni montar un agente con herramientas. La salida se valida extrayendo JSON por regex y los fallos se ocultan con una respuesta stub.

## Decisión
- Nuevo proveedor `claude_cli` en el `factory` existente de ai-parser. Lanza `claude -p --output-format json --json-schema <schema> --model <modelo>` como subproceso asíncrono, usando la suscripción de Claude Code del Arquitecto.
- Los esquemas pydantic son la fuente de verdad: de ellos sale `--json-schema` y con ellos se valida la respuesta.
- Ollama, OpenAI-compatible y stub se mantienen como alternativas (`APP_LLM_PROVIDER`).

## Consecuencias
- ✅ Calidad muy superior sin coste adicional ni API key. Salida estructurada nativa.
- ⚠️ Solo para uso personal y local: la suscripción no cubre servir a varios usuarios ni un despliegue en producción. Para eso hará falta un proveedor `anthropic` (SDK oficial con API key), previsto en M7.
- ⚠️ La latencia por llamada es de segundos (arranca un proceso), así que las llamadas largas van por la cola Redis (M2).
- ⚠️ Requiere que `claude` esté instalado y autenticado en la máquina que ejecuta ai-parser (no funciona dentro de Docker sin configuración extra).
