# Requisitos de producto — TrainingApp

> Fuente de verdad sobre **qué** debe hacer la app. Mantenido por el Arquitecto.
> Estado de cada requisito: [`requirements.yaml`](requirements.yaml). Análisis de brecha: [`GAP_ANALYSIS.md`](GAP_ANALYSIS.md). Plan: [`ROADMAP.md`](ROADMAP.md).

## Visión

App flexible para objetivos deportivos con una IA de fondo. El usuario registra **cualquier** actividad, la app calcula carga/fatiga, analiza su preparación respecto a su **deporte principal** (p. ej. boxeo) y recomienda cambios. La interacción principal es **conversacional y tolerante** (chatbot), no formularios rígidos.

### Fases

| Fase | Objetivo |
| :--- | :--- |
| F1 — Funcional | Todas las capacidades núcleo funcionan de extremo a extremo con datos reales. |
| F2 — Blindaje | Seguridad (auth robusta, autorización por usuario, rate limiting, secretos, auditoría). |
| F3 — Móvil | API versionada y estable consumible por app móvil; registro de datos desde el móvil. |

## Requisitos funcionales

### RF-01 · Registro de cualquier tipo de entrenamiento
- Deportes: gimnasio/fuerza, running, ciclismo, natación, escalada, boxeo/deportes de combate, HIIT, movilidad, y "otro" libre.
- Modelo común (fecha, duración, RPE, notas) + **métricas específicas por deporte** (series/reps/kg; distancia/ritmo/desnivel/FC; rounds/duración round/tipo de trabajo — saco, sparring, manoplas; vías/grado; etc.).
- Entrada por formulario **y** por texto libre/voz parseado por IA ("hoy 5 rounds de saco de 3 min y 20 min de comba").
- Edición y borrado; historial filtrable.

**Aceptación:** registrar una sesión de cada deporte listado, con sus métricas propias, desde formulario y desde texto libre.

### RF-02 · Fatiga y desgaste muscular
- Carga por sesión según deporte, duración, intensidad (RPE/FC) y volumen.
- Reparto de carga por grupo muscular (mapa corporal) también para deportes no-gimnasio (boxeo → hombros, core, piernas…).
- Modelo temporal: acumulación y recuperación (p. ej. ACWR / fitness-fatiga, decaimiento por grupo).
- Alertas: grupo sobrecargado, riesgo por pico de carga.

**Aceptación:** tras registrar sesiones mixtas, el mapa muestra fatiga por músculo que decae con los días y la explicación de su origen.

### RF-03 · Adaptación de rutinas a un deporte concreto
- El usuario define deporte principal, nivel, objetivos y calendario (p. ej. combate en X semanas).
- La IA adapta una rutina de gimnasio existente al deporte (patrones de movimiento, potencia, resistencia específica, prevención de lesiones).

**Aceptación:** dada una rutina genérica y "boxeo", devuelve una rutina modificada con justificación por cambio.

### RF-04 · Análisis y recomendador
- Analiza rutinas y entrenos reales frente al deporte principal: carencias, desequilibrios, rangos de reps/intensidad inadecuados.
- Recomienda ejercicios sustitutos, cambios de series/reps y rutinas completas.
- Recomendaciones basadas en el historial real del usuario, no solo en la rutina declarada.

**Aceptación:** el informe cita datos del usuario (volumen, frecuencia, fatiga) y propone cambios accionables aplicables con un clic.

### RF-05 · Nutrición y calorías
- Registro de comidas buscando alimentos en API externa (FatSecret, Open Food Facts, Edamam…), con macros.
- Entrada por texto libre ("2 huevos y una tostada") y, opcional, código de barras.
- Balance diario: ingesta vs gasto estimado por entrenos.

**Aceptación:** registrar un día completo de comidas y ver kcal/macros y balance frente al gasto.

### RF-06 · Experiencia de gimnasio (biblioteca, rutinas, entreno en vivo, progreso) — PRIORIDAD ALTA
> Objetivo: que el Arquitecto sustituya su app actual de gimnasio por esta, usándola **desde el móvil en el gym**. Mismo género que Jefit/Lyfta, con diseño propio.

**Biblioteca**
- 873 ejercicios de `free-exercise-db` (ya en el repo) con sus 2 imágenes (inicio/fin) animadas, instrucciones traducidas al español y músculos sobre el mapa corporal.
- Búsqueda instantánea, filtros por músculo, equipo y categoría, favoritos y ejercicios personalizados.
- Ficha de ejercicio con historial propio, récords y gráfica (1RM estimado, volumen).

**Rutinas**
- Plantillas y carpetas, superseries, reordenar, notas por ejercicio, series objetivo.
- Programas multisemana y calendario por fechas.

**Entreno en vivo** (el corazón del uso en el gym)
- Empezar desde una rutina o vacío. Muestra por serie lo que hiciste **la última vez**.
- Tipos de serie (calentamiento, normal, drop, al fallo), marcar serie hecha y RPE opcional.
- Temporizador de descanso automático con aviso o vibración.
- Añadir, sustituir o reordenar ejercicios sobre la marcha.
- No se pierde la sesión al recargar o perder cobertura.
- Resumen final: duración, volumen, récords batidos y músculos trabajados.

**Progreso**
- Récords personales, gráficas por ejercicio, calendario y racha, progresión sugerida (doble progresión / RPE).

**UX móvil**
- Uso con una mano, objetivos táctiles grandes y pantalla activa durante el entreno.
- Instalable (PWA) y accesible desde el móvil.

**Aceptación:** hacer una semana real de gimnasio solo con esta app (crear rutina, entrenar desde el móvil viendo la sesión anterior, descansos cronometrados, ver récords y progreso) sin echar de menos la app actual.

### RF-07 · Integración Strava / Garmin
- OAuth con Strava (y Garmin Connect / Health API cuando sea viable).
- Importación automática vía webhook al terminar la actividad; importación histórica.
- Deduplicación y mapeo al modelo de RF-01; la sesión importada alimenta RF-02.

**Aceptación:** al terminar una actividad en Strava aparece en la app en < 5 min sin intervención.

### RF-08 · Interfaz conversacional
- Chat multi-turno con memoria de conversación y acceso (tool use) a los datos del usuario: registrar, consultar, analizar, planificar.
- Flexible: entiende lenguaje informal, pide aclaraciones en vez de fallar.
- Las acciones con efecto (crear/editar datos) se confirman antes de aplicarse.

**Aceptación:** desde el chat se puede registrar un entreno, preguntar "¿cómo voy de fatiga en piernas?" y pedir un ajuste de rutina.

## Requisitos no funcionales

| ID | Requisito |
| :--- | :--- |
| RNF-01 Seguridad | Autenticación robusta (tokens de corta vida + refresh), autorización por recurso/usuario, rate limiting, validación de entrada, secretos fuera del repo, OWASP API Top 10. |
| RNF-02 Móvil/API | API REST versionada (`/api/v1`), contrato OpenAPI estable, paginación, errores homogéneos, CORS controlado. |
| RNF-03 IA | Salida LLM validada por esquema, timeouts y fallback, guardarraíles ante prompt injection, coste por petición acotado, trazabilidad. |
| RNF-04 Calidad | Tipado estricto, tests unitarios por componente, CI verde, ADRs para decisiones. |
| RNF-05 Privacidad | Datos de salud: export y borrado de cuenta (RGPD), mínimo de datos a terceros (LLM). |
| RNF-06 UX | Responsive/mobile-first, español primero (i18n preparada), estados de carga y error. |
