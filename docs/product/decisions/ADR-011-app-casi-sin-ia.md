# ADR-011 · App casi sin IA: conocimiento + motores deterministas

**Estado:** Aceptada e implementada (P0-P5) · 2026-11-13 · M10

## Problema
Casi todo el chat y la creación de planes pasaba por Claude: 2-3 llamadas por mensaje, 8-16 s de espera y la app quedaba inservible si la IA fallaba o se encarecía. Medido: 11 escenarios = 17 llamadas, 72k tokens, 107 s.

## Decisión
- El núcleo son **datos versionados** (perfiles de deporte con cualidad→patrones→foco y objetivos; `exercise_tags.json` con material y patrones) y **motores deterministas** (alternativas por condición, recomendador por objetivo, generador de planes por árbol, diccionario de comidas).
- **Router único en el servidor** delante del agente: lo que encaja se responde con tarjetas sin IA; lo demás va al agente (patrón strangler). Interruptores por nodo.
- La IA queda como **capa opcional**: lenguaje libre, comidas nuevas (lo que calcula se guarda para siempre), redacción. Proveedor y modelo elegibles por tarea.
- **No** se adoptan LangGraph, Neo4j, pgvector, LlamaIndex ni Pydantic AI: Postgres + funciones tipadas bastan. Revisar LangGraph si llegan flujos largos con pausas (adaptación semanal del plan con aprobación).
- USDA apagado: comidas = diccionario propio + Open Food Facts.

## Consecuencias
- ✅ Medido: 6 llamadas, 19k tokens, 53 s (de 17 / 72k / 107 s); lo frecuente responde al instante.
- ✅ Sin IA la app sigue creando planes, alternativas, recomendaciones y comidas conocidas.
- ⚠️ La calidad depende del mapa: hay que mantener perfiles y etiquetas (Claude puede redactarlos offline; los tests validan que todo nombre existe).
- ⚠️ Lo aprendido por la IA en comidas es compartido; las correcciones de ración son por usuario.
- ⚠️ El generador por LLM sigue disponible (`APP_PLAN_ENGINE=llm`) hasta comparar con uso real.
