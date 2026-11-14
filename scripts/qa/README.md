# Batería QA (modo reglas frente a modo IA)

Prueba de extremo a extremo con la app real y usuarios de prueba (`@qa.traingapp.dev`) sobre una **copia** de la base de datos. Compara cada escenario en modo reglas (lo actual) y en modo IA (router apagado y planes con Claude). Un juez (Claude, a ciegas) puntúa las dos respuestas.

## 1. Preparar la copia de la base de datos

```bash
docker exec traingapp-postgres sh -c 'dropdb -U traingapp --if-exists traingapp_qa && createdb -U traingapp traingapp_qa && pg_dump -U traingapp -d traingapp | psql -q -U traingapp -d traingapp_qa'
docker exec traingapp-postgres psql -U traingapp -d traingapp_qa -c "delete from food_alias;"   # diccionario de comidas vacío
```

## 2. Arrancar los servicios de prueba (4 terminales)

```bash
# ai-parser con Claude y medidor de tokens (el medidor está en el scratchpad de la sesión que lo creó;
# sin él, usa el ai-parser normal en 8101 y omite --meter-log no es posible: el informe necesita el log)
cd services/ai-parser && .venv/Scripts/python <ruta>/ai_parser_meter.py <log>.jsonl 8101
# ai-parser sin IA (referencia determinista)
cd services/ai-parser && APP_LLM_PROVIDER=stub .venv/Scripts/python -m uvicorn app.main:app --port 8102
# gateway modo reglas
cd services/api-gateway && APP_DATABASE_URL=postgresql+asyncpg://traingapp:traingapp@localhost:5432/traingapp_qa APP_REDIS_URL=redis://localhost:6379/1 APP_AI_PARSER_URL=http://127.0.0.1:8101 APP_GARMIN_POLL_MINUTES=0 .venv/Scripts/python -m uvicorn app.main:app --port 8001
# gateway modo IA (lo de antes)
cd services/api-gateway && APP_DATABASE_URL=…/traingapp_qa APP_REDIS_URL=redis://localhost:6379/1 APP_AI_PARSER_URL=http://127.0.0.1:8101 APP_CHAT_RULE_NODES=guided APP_PLAN_ENGINE=llm APP_GARMIN_POLL_MINUTES=0 .venv/Scripts/python -m uvicorn app.main:app --port 8002
```

## 3. Ejecutar

```bash
services/api-gateway/.venv/Scripts/python scripts/qa/battery.py --meter-log <log>.jsonl --out <carpeta>
```

Genera `<carpeta>/results.json` con, por escenario, la salida de cada modo, el uso (llamadas a IA, tokens, segundos), las comprobaciones automáticas y el veredicto del juez.

## Personas y escenarios

- **Runner** (en casa), **boxeador** (gimnasio sin balón medicinal) y **solo gym** (principiante): batería completa.
  - Crear plan con el asistente guiado.
  - Chat: objetivo, «qué me toca», fatiga, material que falta y una pregunta abierta.
  - Análisis de la rutina.
- **Futbolista** y **HYROX**: crear plan y objetivo. Validan los mapas nuevos.
- **Entreno por texto:** lista estructurada (sin IA) frente a IA, y un texto libre.
- **Comidas:**
  - primera vez (con IA), segunda vez (diccionario) y otro usuario;
  - corrección de ración, que se guarda solo para quien la hace;
  - apuntar comida desde el chat.

Coste orientativo: 80-90 llamadas a Claude (incluido el juez), unos 30-40 minutos.
