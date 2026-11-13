# ADR-010 · Correcciones del primer uso real en el gimnasio (feature/corrections)

Fecha: 2026-11-13 · Estado: aceptado (pendiente de validar en uso real)

## 1. Gasto calórico: modo "según lo que registro" o "estimado"
- **Problema:** el factor de actividad es el día a día SIN deporte, y las kcal de los entrenos de hoy ya se suman. Quien eligía "Activa" porque entrena contaba el deporte dos veces. Quien no registra siempre no tenía una opción coherente.
- **Decisión:** `nutrition_goal.activity_mode` (migración `k2l3m4n5o6p7`):
  - `registro` (por defecto, recomendado): factor 1,2-1,6 solo para la vida diaria, más las kcal reales de los entrenos de cada día. Un día de boxeo de 800 kcal sube el objetivo 800; un día de gimnasio de 200 lo sube 200.
  - `estimado`: factor 1,4-1,9 con el deporte incluido; no se suman los entrenos.
- **Consecuencia:** el objetivo diario sigue la actividad real del día (no se usa una media semanal). La UI invita a registrar. Pendiente para M10: proponer el modo automáticamente según la constancia de registro, y la actividad diaria con los pasos de Garmin (hoy no se guardan).

## 2. Rutinas recomendadas que puntuaban ~58/100
- **Problema:** el LLM genera la rutina sin conocer los objetivos que usa "Analizar". Además, la nota era todo o nada en zonas de repeticiones, pasarse de rango contaba como medio fallo, y salían todas las carencias a la vez.
- **Decisión:**
  - (a) `services/plan_repair.complete_plan`: después de generar el plan, una pasada determinista añade los patrones que faltan (mismo analizador y mismo perfil que "Analizar"). Elige el ejercicio del catálogo, reparte entre días (máx. 8 ejercicios por día y 6 añadidos), prescribe las repeticiones según la zona que falte y deshace lo que empeore la nota. Objetivo: 80.
  - (b) Nota más justa: crédito parcial en músculos y zonas, y "por encima de rango" vale 0,85. La UI muestra solo las 3 carencias principales.
- **Consecuencia:** es un puente; lo sustituye el generador determinista de M10-F5.

## 3. Manda lo que se practica, no lo planificado
- **Decisión:** "Analizar rutina" incluye `adherence`:
  - % de series planificadas que se hacen de verdad.
  - Puntuación de lo practicado.
  - Ejercicios que te saltas y ejercicios que haces fuera de la rutina.
- Tras cada entreno, `/analysis/week-feedback` da una frase determinista con la mayor carencia de los últimos 7 días frente al deporte principal.
- **Consecuencia:** las sesiones de deporte (boxeo, carrera) no cuentan como patrones de fuerza; necesita datos por deporte (M10-F3).
