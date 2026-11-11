# ADR-002 · Proveedor LLM: Claude vía CLI local

**Estado:** Aceptada e implementada · 2026-11-12 · M2

## Problema
ai-parser usa por defecto `stub` (sin LLM) o un modelo local de 3B (Ollama). La calidad no alcanza para analizar rutinas, adaptar a un deporte ni montar un agente con herramientas. La salida se valida extrayendo JSON por regex y los fallos se ocultan con una respuesta stub.

## Decisión
- Nuevo proveedor `claude_cli` en el `factory` existente de ai-parser. Lanza `claude -p --output-format json --json-schema <schema> --model <modelo>` como subproceso asíncrono, usando la suscripción de Claude Code del Arquitecto.
- Los esquemas pydantic son la fuente de verdad: de ellos sale `--json-schema` y con ellos se valida la respuesta.
- Ollama, OpenAI-compatible y stub se mantienen como alternativas (`APP_LLM_PROVIDER`).

## Implementación (M2)
- `ai-parser/app/llm/claude_cli.py`: `claude -p --model <m> --output-format json --json-schema <schema> --system-prompt-file <f> --tools "" --no-session-persistence`, con el prompt del usuario por stdin y `cwd` en un directorio temporal (así no carga CLAUDE.md ni AGENTS.md del repo). La salida validada llega en el campo `structured_output` del envoltorio JSON.
- Sustituir el prompt de sistema de Claude Code reduce cada llamada de unos 40.000 a unos 1.600 tokens. No se usa `--bare`, porque solo acepta API key.
- Todos los proveedores implementan `complete_json(system, user, schema)`; `llm/structured.generate()` valida con pydantic y repara una vez.
- Medido: parseo de texto libre en unos 5 s y revisión de rutina en unos 20 s (Sonnet).

## Consecuencias
- ✅ Calidad muy superior sin coste adicional ni API key. Salida estructurada nativa.
- ⚠️ Solo para uso personal y local: la suscripción no cubre servir a varios usuarios ni un despliegue en producción. Para eso hará falta un proveedor `anthropic` (SDK oficial con API key), previsto en M7.
- ⚠️ La latencia por llamada es de segundos (arranca un proceso). Basta con llamadas síncronas con timeout acotado, ver [ADR-003](ADR-003-llamadas-llm-sincronas.md).
- ⚠️ Requiere que `claude` esté instalado y autenticado en la máquina que ejecuta ai-parser (no funciona dentro de Docker sin configuración extra).
