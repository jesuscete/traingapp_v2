# ADR-005 · Fatiga por series reales, 1RM único y registro de deporte

**Estado:** Aceptada · 2026-11-12 · Hito M4.1 ([análisis](../ANALISIS_TECNICO.md))

## Problema
- **Fatiga:** el gym repartía la carga con pesos fijos de "gym" (un día de pierna fatigaba más el pecho que los cuádriceps), y la "doble exponencial" era en realidad una sola, con vida media de unas 27 h para todos los grupos.
- **1RM:** cuatro implementaciones (Epley) con límites distintos; una sin límite de repeticiones.
- **Conocimiento por deporte:** repartido entre tablas, prompts genéricos y código.

## Decisión
1. **Carga por músculo desde las series reales** (`services/fatigue_input.py`):
   - Cada serie de trabajo suma `esfuerzo(RPE) × implicación` del músculo, con el músculo principal a 1, a partir de las proporciones del catálogo. Por ejemplo, dominadas: espalda 1, bíceps 0,33.
   - Impulso por grupo: `100 · (1 − e^(−series_efectivas / 6))`; 6 series dan el 63 % y 10 series el 81 %.
   - En combate, cada tipo de bloque carga sus músculos (comba → gemelos; saco → hombros) con los pesos del registro.
   - En el resto de deportes, pesos de la disciplina con una **curva saturante** en lugar del tope duro.
2. **Dos compartimentos reales** por grupo (`analytics/fatigue.py`):
   - Agudo: 35 % del impulso, τ = 0,5 días.
   - Residual: 65 %, con τ por grupo, de 3,0 días (cuádriceps, isquios) a 1,6 (antebrazos).
   - La proyección (mañana, pasado…) usa los dos estados. La calibración personal sigue escalando el τ residual.
3. **1RM único:** tabla RPE→%1RM de RTS (`analytics/strength.py`).
   - Sin RPE asume RPE 10; no estima por encima de 12 repeticiones.
   - Copia exacta en `web/lib/strength.ts`, con los mismos vectores de prueba.
4. **Registro de deporte en el repo** (`data/sport_profiles/*.json`, validado con pydantic al cargar):
   - Boxeo (con alias de artes marciales) y genérico.
   - Lo consumen el analizador (M4), la fatiga (pesos por bloque), la narrativa (`perfilDeporte`) y la herramienta del agente `perfil_deporte`. Resumen compacto de unos 600 tokens.
   - Se eligen ficheros versionados en lugar de una tabla en BD: se revisan en los PR y no hace falta una interfaz de edición. Si en el futuro se edita desde la app, se migra a una tabla.

## Consecuencias
- ✅ La fatiga refleja lo que entrenas y la recuperación de los grupos grandes dura 3-4 días.
- ✅ El mismo 1RM en el historial, los récords y el resumen del entreno.
- ✅ Añadir un deporte es añadir un JSON validado.
- ⚠️ Las constantes (τ, 35/65, 6 series) son razonables pero no están calibradas con tus datos: la tabla de agujetas (`daily_muscle_doms`) permitirá ajustarlas.
- ⚠️ El catálogo de free-exercise-db reparte por igual entre los músculos secundarios: los ejercicios propios (44) están mejor graduados.
- ⚠️ Los prompts de planes antiguos (`training_prompt`) siguen existiendo hasta que el agente genere los planes.
