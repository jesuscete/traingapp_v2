# Plan de arreglos (roadmap)

> Plan propio, derivado del análisis del código ([GAP_ANALYSIS.md](GAP_ANALYSIS.md)). **No** se basa en los planes ni ADRs previos de OpenCode (`docs/architecture/*`). Cada hito se divide en micro-iteraciones que se aprueban antes de ejecutarlas (AGENTS.md §4). Al cerrar un hito, actualizar [requirements.yaml](requirements.yaml).

## 📍 Estado actual (2026-11-12)

| Hito | Estado |
| :-- | :-- |
| M0 Saneamiento | ✅ |
| M1 Gimnasio | ✅ (falta probarlo en el móvil) |
| M2 IA con Claude | ✅ |
| M3 Multideporte y fatiga | ✅ |
| M4 Deporte principal y agente | ✅ |
| M4.1 Mejoras encontradas | ✅ fatiga, 1RM y registro de deporte |
| M5 Nutrición | ✅ |
| **M5.1 Prueba en el móvil y pulido** | 🟡 rondas 1 y 2 hechas; seguir probando en uso real |
| M6 Actividades de reloj | ✅ M6.1 archivos · ✅ M6.2 Garmin · M6.3 global → después de M8 |
| M7 Blindaje | 🟡 parcial |
| M8 App móvil | 🟡 parcial (PWA, `-Lan`, `-Https`) |

- **Código:** todo en `feature/refactor`. Pasan los tests del gateway (315) y de ai-parser (68); `ruff`, `mypy`, `tsc` y `next build` sin errores.
- **Pendiente tuyo:**
  - Probar M1-M4 en el móvil.
  - mkcert (`-Https`) pasa al backlog: primero, la app funcional en uso real.
  - Hacer merge de tus cambios locales en `fatiga/page.tsx`, `MuscleChart.tsx` y `routineReview.ts`.

## Principios de orden
1. **Usable cuanto antes en la vida real:** la experiencia de gimnasio (RF-06) va primero, porque el Arquitecto la usará a diario y eso genera datos reales para todo lo demás.
2. **IA fiable antes que funciones de IA:** el adaptador de Claude va antes del agente y del recomendador.
3. **Seguridad mínima ya** (bugs triviales en M0). El blindaje completo va antes de la app móvil nativa.

## Decisiones tomadas
- **LLM:** se usa Claude a través del CLI local `claude -p --json-schema` (suscripción de Claude Code) como un nuevo proveedor del `factory` existente de ai-parser. Ollama y stub se mantienen. Más adelante se podrá cambiar a la API de Anthropic (SDK `anthropic`) sin tocar los servicios. *Límite:* sirve para uso personal y local, no para varios usuarios ni producción (ahí hará falta una API key). Ver [ADR-002](decisions/ADR-002-proveedor-llm.md).

## Hitos

### M0 · Saneamiento ✅ (2026-11-11)
- [x] Un token con `sub` malformado devuelve 401 en vez de 500. `hmac.compare_digest` en `/internal`.
- [x] Con `APP_ENV=production` no se arranca si hay secretos por defecto (gateway y ai-parser). CORS configurable con `APP_CORS_ORIGINS`.
- [x] Tests de aislamiento entre usuarios en los endpoints `/{id}`: sin fugas. Las claves de Redis (live, plan, borradores) van ligadas al usuario.
- [x] Higiene: los logs de `dev-up.ps1` van a `logs/`, se borraron logs y caché obsoleta y hay un README real en web.
- [x] Modelo de sesiones: [ADR-001](decisions/ADR-001-modelo-sesiones.md). Proveedor LLM: [ADR-002](decisions/ADR-002-proveedor-llm.md).

### M1 · Experiencia de gimnasio (RF-06) ✅ (2026-11-12, falta probarla en el móvil)
- [x] ADR-001 aplicado; `migrate_legacy_gym` ejecutado (0 sesiones que migrar).
- [x] Biblioteca: imágenes, búsqueda sin tildes, filtros, favoritos, **ejercicios propios** (crear/borrar, aislados por usuario), ficha con récords, 1RM e historial.
- [x] Traducción al español (873 ejercicios). Los ejercicios se resuelven por `exerciseId` y por nombre en español (corregida la pérdida de historial y de impactos musculares).
- [x] Entreno en vivo: estado local persistente, "Anterior", tipos de serie, descanso con vibración, superseries, cola offline idempotente (`clientId`), resumen con récords.
- [x] Rutinas: duplicar (plantilla), reordenar, notas y superseries en el editor; las notas pasan al entreno. Validación de ejercicios ajenos o inexistentes (422).
- [x] PWA (manifest), `dev-up.ps1 -Lan` y `-Https` (mkcert) para instalarla de verdad en el móvil.
- [ ] Probar en el móvil en el gym y ajustar la UX.
- [ ] *Aplazado:* carpetas de rutinas, programas multisemana, progresión sugerida (al planificador de M4).

### M2 · IA fiable con Claude (RNF-03) ✅ (2026-11-12)
- [x] Proveedor `claude_cli` (ADR-002), activo en el `.env` local; Ollama y OpenAI se mantienen.
- [x] Salida estructurada nativa en los 3 proveedores + validación pydantic + 1 reintento de reparación (`llm/structured.py`). Eliminada la extracción por regex.
- [x] `source: llm|fallback` en todas las respuestas de ai-parser y en `/routines/review` (con indicador en la web). Solo se captura `LLMError`, y el fallo se registra en el log antes del fallback.
- [x] `X-Internal-Token` obligatorio en ai-parser; datos del usuario delimitados (`<datos_usuario>`). Probado: ignora la inyección de prompt y la anota.
- [x] Timeouts coherentes (90 s / 200 s). **Cambio:** sin cola, ver [ADR-003](decisions/ADR-003-llamadas-llm-sincronas.md).
- [x] Corregido: el prompt de revisión pedía `solapamientos` como texto y el código los descartaba todos.

### M3 · Registro multideporte y fatiga (RF-01, RF-02) ✅ (2026-11-12)
- [x] Métricas por deporte validadas (`schemas/metrics.py`, en `details.metrics`): combate (bloques saco/sparring/manoplas/comba/sombra/técnica/físico con rounds×duración o minutos), resistencia (distancia, FC, desnivel), escalada (estilo + vías con grado), genérica. Se rechazan las que no encajan con la disciplina (422).
- [x] La duración se deriva de los bloques; la distancia, la FC y el desnivel alimentan sus columnas y las kcal.
- [x] Fatiga: volumen de combate a partir de los bloques (golpes equivalentes por tipo), ciclismo y natación por km con pendiente, artes marciales como combate.
- [x] **Fix:** la fatiga y las kcal ignoraban `intensity` (las 30 sesiones de gym contaban con RPE 5). Ahora: `details.rpe` → `intensity` → RPE medio de las series.
- [x] `GET /stats/fatigue/explain?group=`: descomposición exacta de la fatiga actual por sesión.
- [x] `PUT /sessions/{id}`: edición parcial (en gym solo los datos generales).
- [x] IA: el parseo extrae bloques de combate y datos de resistencia, y el chat los guarda al confirmar (probado con Claude: 4,9 s).
- [x] Web: `/registrar` con formulario por deporte, detalle y edición de sesiones, explicación de la fatiga en el dashboard y métricas en el borrador del chat.
- [ ] *Aplazado:* retirar la tabla `exercises` (segunda parte del ADR-001); dividir una sesión mixta en varias.

### M4 · Deporte principal y agente (RF-03, RF-04, RF-08) ✅ (2026-11-12)
- [x] Perfil de demandas del boxeo (`analytics/sport_analysis.py`): patrones (rotación, anti-rotación, pliometría, explosivos, unilateral, bisagra, cuello, tirones), rangos de series por músculo, zonas de repeticiones, equilibrio tirón/empuje y conflictos con los días de deporte. Hay un perfil genérico para el resto de deportes.
- [x] Clasificación de patrones de movimiento por ejercicio (`analytics/patterns.py`).
- [x] `GET /analysis/sport`: análisis determinista del historial (≥3 sesiones en 4 semanas) o de la rutina activa, con puntuación, carencias y ejercicios sugeridos. Con `narrative=true`, Claude redacta el diagnóstico y las prioridades.
- [x] Recomendador: `GET /catalog/exercises/{id}/alternatives` (similitud muscular, de fuerza y de patrón) y aplicar con un clic (`POST /routines/{id}/exercises/{eid}/swap`, `POST /routines/{id}/days/{dow}/exercises`).
- [x] Agente conversacional con 10 herramientas, memoria y confirmación antes de escribir ([ADR-004](decisions/ADR-004-agente-conversacional.md)). Probado con Claude: 8-14 s por turno.
- [x] Motor de fatiga movido a `services/fatigue_engine.py` (lo comparten las estadísticas y el agente).
- [ ] *Aplazado:* mover `web/lib/routineReview.ts` al backend (es un fichero con cambios locales del Arquitecto); planes multisemana generados por el agente.

### M4.1 · Mejoras encontradas ✅ (2026-11-12, [ADR-005](decisions/ADR-005-fatiga-1rm-registro-deporte.md))
Origen: [ANALISIS_TECNICO.md](ANALISIS_TECNICO.md) §2, §3 y §5.
1. **Fatiga realista**
   - [x] Cada ejercicio y cada deporte carga sus músculos con su nivel de implicación (p. ej. dominadas: espalda > bíceps > antebrazo). La carga de gym sale de las **series reales** (activación × esfuerzo por serie).
   - [x] Recuperación en **dos compartimentos reales** (agudo y residual) con τ por grupo muscular, más prolongada en grupos grandes y excéntricos.
   - [x] Deportes: pesos musculares por tipo de bloque (comba, saco, sparring…).
2. **1RM único y fiable**
   - [x] Una sola fórmula en toda la app: tabla RPE→%1RM (RTS); sin RPE asume RPE 10; 1-12 reps. Backend `analytics/strength.py` y web `lib/strength.ts`, con los mismos vectores de prueba.
3. **Registro de conocimiento por deporte**
   - [x] Perfil estructurado por deporte (boxeo el primero): cualidades, patrones, ejercicios clave, series por músculo, zonas de reps por fase, lesiones y prehab, reglas de calendario y carga por bloque.
   - [x] La IA lo consulta (prompt compacto + herramienta `perfil_deporte`) en vez de deducirlo.

**Backlog de mejoras** (después de M5): progresión sugerida (doble progresión), kcal por FC (Keytel), retirar `chat/plan_session.py`, imágenes sin conexión, sesiones mixtas.

### M5 · Nutrición (RF-05) ✅ (2026-11-12, [ADR-006](decisions/ADR-006-nutricion.md))
- [x] Fuentes: Open Food Facts (código de barras y marcas de España) + USDA (genéricos) + Claude (texto libre), con caché local.
- [x] Modelo: `food`, `meal_entry` (copia de macros + método), `meal_template`, `body_weight_log`, `nutrition_goal`. Migración `a2b3c4d5e6f7`.
- [x] Objetivo diario: Mifflin-St Jeor × actividad + **kcal reales de los entrenos** ± objetivo (perder, mantener, ganar o **corte hacia una categoría**), con límites de seguridad; macros por g/kg.
- [x] **Registro exacto** (gramos de báscula, etiqueta) y **estimado** (raciones, rápido, texto libre con IA); el día separa las kcal exactas de las estimadas.
- [x] Texto libre: Claude estima → se contrasta con tus alimentos y con USDA, **solo si las kcal son plausibles** (corregido: el café con leche salía con 1.098 kcal).
- [x] Búsqueda, código de barras, mis platos, peso con media de 7 días, agente (`registrar_comida` propone, `ver_nutricion`).
- [x] Web: `/comidas` (anillo de kcal, macros, exacto/estimado, comidas, añadir por 5 vías, peso, objetivo) y tarjeta "Hoy comido" en el dashboard.
- [x] Clave de USDA configurada en `.env` local.
- [ ] Probarlo en el móvil. El escáner con cámara ya funciona con HTTPS (Tailscale, M8).

### M5.1 · Prueba en el móvil y pulido 🟡
- [x] Ronda 1 de pulido tras el uso real (2026-11-12):
  - **Navegación nueva:** Inicio · Entrenar · Comidas · Progreso · Coach. El perfil, los objetivos y la configuración están en el avatar.
  - **Hubs:** Entrenar (gimnasio, registrar, importar, rutinas, ejercicios) y Progreso (avance semanal, historial, fatiga, preparación, carga, peso).
  - **Inicio rediseñado:**
    - Avisos deterministas (`GET /stats/home`): días sin registrar, fatiga alta (descanso), sobrecarga (ACWR), subida brusca de volumen, proteína, peso frente al objetivo y "vas bien".
    - Mapa corporal de fatiga, semana por deporte (minutos, no kg), comida de hoy y actividad reciente.
    - Fuera el volumen en kg semanal y de 90 días.
  - **Mapa del recorrido** con OpenStreetMap (Leaflet). Se guardan lat/lon de FIT, GPX y TCX. Las actividades importadas antes no tienen coordenadas: hay que reimportarlas.
  - **Fatiga en el detalle de la sesión:** se arregló que todo saliera como "otros" (zona deducida del grupo). Además, mapa corporal con alternativa de radar.
  - **Búsqueda de ejercicios bilingüe:** "bench press" encuentra "Press banca" (alias en inglés de los ejercicios canónicos).
  - **Chat:** se explica el límite de uso de Claude en lugar de "no disponible" sin motivo. El error se lee del JSON de stdout del CLI.
- [x] Ronda 2 (2026-11-12):
  - **Iconos de línea** (lucide) en lugar de emojis y tarjetas homogéneas en los hubs.
  - **Mis objetivos** (`/objetivos`): deporte principal, otros deportes y metas con fecha (peso, prueba, competición, marca). La meta principal sale en Inicio con cuenta atrás.
  - El **deporte principal** manda en la preparación, en el análisis y en el Coach. Nuevo perfil de **triatlón**, que también cubre running, ciclismo y natación.
  - **Preparación para tu deporte** de vuelta en Inicio.
  - **Analizar** cada rutina → «Preparar rutina con estos cambios» abre el Coach con la petición; tú confirmas los cambios que proponga.
  - Distancia e insignia «Garmin» en la actividad reciente. El Coach conoce tus metas.
- [ ] Seguir probando en uso real y anotar ajustes.

### M6 · Actividades de reloj: archivos → Garmin → global (RF-07)
**Decisión:** fuente = **el reloj** (archivo FIT/GPX/TCX y API de Garmin), no Strava. El acuerdo oficial de la API de Strava (2026) prohíbe usar sus datos en aplicaciones de IA (incluido el contexto de un LLM) y guardarlos más de 7 días, lo que choca con el historial y con el agente. Los datos que vienen directamente del reloj son del usuario y no tienen esas restricciones.

**Multideporte:** el FIT trae el deporte de cada actividad, así que el importador sirve para todo: running, ciclismo, natación (largos y brazadas), cardio/HIIT, senderismo, remo… y **fuerza** (Garmin guarda las series, repeticiones y ejercicios, que se mapean al modelo de gym).

#### M6.1 · Importar archivos a mano ✅ (2026-11-12, [ADR-007](decisions/ADR-007-importacion-actividades.md); falta probarlo con un .fit real de tu Garmin)
- [x] Perfil: **FC máxima** (191 en tu caso) y **FC en reposo** (opcional). Si faltan: FC máxima estimada (208 − 0,7·edad) y FC en reposo estimada. **Se aprenden solas:** si una actividad supera tu FC máxima se propone actualizarla; la FC en reposo llegará de Garmin (M6.2).
- [x] Subir uno o varios archivos **FIT, GPX o TCX** desde la web/móvil (también para importar el historial de golpe).
- [x] Lector (`fitdecode` + GPX/TCX): resumen (deporte, inicio, duración, distancia, desnivel, FC media y máxima, cadencia, potencia, kcal del reloj), **series temporales** (FC, ritmo/velocidad, altitud, cadencia, potencia), **vueltas y parciales por km**; natación: largos/estilo; fuerza: series y repeticiones.
- [x] Mapeo del deporte del FIT → disciplina de la app (running, cycling, swimming, gym…) y sus métricas de resistencia (M3). Lo desconocido va a "other" con aviso.
- [x] **Deduplicación:** `external_source` + `external_id` (o huella del archivo) y comprobación de solapamiento horario con sesiones registradas a mano (propone fusionar).
- [x] **Zonas de FC:** 5 zonas por reserva de FC (Karvonen), **tiempo en cada zona** y **TRIMP** (carga por FC).
- [x] La actividad alimenta: **fatiga** (carga por TRIMP/FC en lugar de solo duración), **kcal** (ecuación por FC, Keytel), balance de comidas, análisis del deporte y agente.
- [x] Web: botón "Importar actividad" y detalle con **gráficas de FC y ritmo, parciales, tiempo en zonas** y mapa de desnivel.

#### M6.2 · Conexión automática con Garmin ✅ (2026-11-12, [ADR-008](decisions/ADR-008-garmin-api-personal.md))
- [x] Clave personal de la API oficial de Garmin (gratuita, solo lectura): conectar en **Configuración → Garmin**, clave y token **cifrados**, desconectar.
- [x] Sincronización: la API personal no envía avisos, así que hay sondeo cada 30 min, sincronización al abrir Inicio (si hace más de 15 min) y botón «Sincronizar ahora». Las actividades entran por el importador de M6.1, sin duplicar lo subido a mano.
- [x] Validado con tu cuenta real (2026-11-12): actividades y FC en reposo llegan (13 días). El sueño de esos días vino vacío desde Garmin, y la VFC «sin datos» (tu reloj no la envía) ya no da error. Falta comprobar el sueño una noche con el reloj puesto.
- [x] Salud diaria → readiness de la fatiga: FC en reposo, sueño y VFC. Estrés y Body Battery llegan en la respuesta, pero aún no se usan (backlog).
- [x] Historial: 30 días al conectar y botón «Traer últimos 90 días». Insignia «Garmin» en las actividades sincronizadas.

#### M6.3 · Global (después de M8, con la app nativa)
- [ ] **Health Connect** (Android) / **HealthKit** (iOS): reciben datos de casi cualquier reloj o app (Coros, Polar, Samsung, Apple…).
- [ ] El importador de archivos de M6.1 ya cubre cualquier marca mientras tanto.

### M6-7 · Alta de usuario y bienvenida 🟡 (previa a M7)
Objetivo: empezar a usar la app con tu propio usuario, creado desde cero como cualquier persona nueva (alex@traingapp.dev queda solo para pruebas).
- [x] Página de registro (`/registro`) con «Recuérdame». El login enlaza a ella.
- [x] Bienvenida: mientras falten los datos imprescindibles (peso, altura, fecha de nacimiento, sexo y deporte principal), aparece un formulario para rellenarlos. Al completarlos, no vuelve a salir.
- [x] «Saca más partido a la app»: conectar Garmin, definir el objetivo, otros deportes y FC máxima. Cada paso se puede omitir y desaparece al hacerlo (`GET /profile/onboarding`).
- [ ] Crear tu usuario real y empezar a meter datos.

### M7 · Blindaje para abrir la app fuera de casa ✅ (2026-11-12, [ADR-009](decisions/ADR-009-blindaje-sesiones.md))
Objetivo: usar la app fuera de casa con seguridad. **Decisión (2026-11-12): Tailscale** (red privada entre el PC y el móvil, sin abrir puertos y con HTTPS válido). El servidor es tu PC encendido; más adelante se puede pasar a un VPS.
- [x] Token de acceso de 15 min con refresh rotatorio, detección de reutilización, cierre de sesión y cierre en todos los dispositivos.
- [x] Límite de intentos de login y de registro. Recuperar la contraseña desde el PC (`python -m app.cli reset-password`).
- [x] Cabeceras de seguridad (API y web). Postgres y Redis solo en localhost. Secretos fuertes (`python -m app.cli init-secrets`).
- [x] Next.js 16.4.6: corrige una vulnerabilidad crítica. `npm audit` sin vulnerabilidades.
- [x] RGPD: descargar tus datos y borrar la cuenta (Configuración → Cuenta y seguridad).
- [x] Copias de seguridad: `scripts/backup-db.ps1` y `restore-db.ps1`; copia diaria con `register-backup-task.ps1`.
- [x] Validado con tu Garmin real: la FC en reposo llega (`heartRate.restingValue`) y «sin VFC» ya no da error.
- [ ] Pendiente para cuando haya más usuarios: verificación de email y reseteo por correo (SMTP), cookie httpOnly (con HTTPS, M8), pip-audit en CI y proveedor LLM de producción.

### M8 · App instalada en el móvil y uso fuera de casa ✅ (2026-11-12; falta la prueba en el gimnasio)
Objetivo: la app instalada en el móvil, usable en el gimnasio con conexión segura (HTTPS), para registrar entrenos en uso real.
- [x] `dev-up.ps1 -Tailscale`: servicios solo en localhost y `tailscale serve` con HTTPS válido en `https://traingapp.tail965cc3.ts.net`. La web va en `/` y la API en `/api` (mismo origen); `dev-down` retira la publicación.
- [x] PWA instalable: manifest con iconos PNG (incluido maskable), atajos y botón «Instalar la app» en Configuración.
- [x] Service worker: la app abre sin conexión (páginas y estáticos guardados; API con red primero y caché del móvil, nunca `/api/auth`). Al cerrar sesión se borra la caché.
- [x] Ya existían y ahora funcionan con HTTPS: pantalla encendida durante el entreno (Wake Lock), escáner con la cámara (BarcodeDetector) y cola de entrenos sin conexión.
- [ ] Prueba real: instalar en el móvil y registrar un entreno con datos móviles (Wi-Fi apagado), también sin cobertura.
- [ ] Prefijo `/api/v1`, errores RFC 7807, paginación coherente.
- [ ] Tipos generados desde OpenAPI para web y móvil.
- [ ] App nativa (React Native/Expo reutilizaría TypeScript) frente a seguir con la PWA: decidir.

### M9 · Pulido con el uso real ⏳ (siguiente)
Lo encontrado al usar la app instalada en el móvil (2026-11-12). Orden propuesto: 1 → 2 → 3.

**1. Comidas: que aparezca lo normal de alguien que entrena**
- **Problema:** «leche» devuelve 1 resultado (un chocolate con leche), «proteína en polvo» y «whey» devuelven 0, y «cereales integrales» devuelve pan de molde.
- **Causas:**
  - Open Food Facts devuelve productos de marca ordenados por popularidad, no alimentos genéricos.
  - USDA está en inglés.
  - No hay sinónimos.
- **Propuesta:**
  - **Base propia de alimentos genéricos** (unos 300-500: lácteos, cereales y copos, legumbres, carnes, pescados, huevos, frutas, verduras, frutos secos, aceites, suplementos como proteína whey/caseína/vegana, creatina, ganadores…). Valores de una tabla oficial (BEDCA/AESAN o USDA) y nombres en español con sinónimos («leche semidesnatada», «copos de avena», «whey»). Se busca primero y responde al momento, sin internet.
  - **Mejor búsqueda en Open Food Facts:** la API de búsqueda nueva, filtrar por España y ordenar por coincidencia. Traducción ES→EN para USDA.
  - **Tus alimentos frecuentes y recientes** arriba del todo. Crear alimentos propios (ya existe) desde la etiqueta, o con la foto de la etiqueta más adelante.

**2. Navegación y densidad de información**
- **El chat choca con el círculo del perfil** en la app instalada: hay que recolocar el botón del chat y el avatar.
- **Demasiados datos por pantalla:** priorizar, plegar los detalles («ver más») y dejar menos texto y más visual. Revisar pantalla a pantalla: Inicio, Entrenar, Comidas y Progreso.
- **Recorridos cortos para lo frecuente:** empezar entreno, añadir comida y ver hoy, a uno o dos toques desde Inicio.

**3. Estética: un sistema visual y adaptación móvil/escritorio** → análisis completo y propuesta en [DISENO_UI.md](DISENO_UI.md). ✅ F1-F5 hechas (2026-11-12); falta la revisión visual y elegir el color por defecto
- **Sistema de diseño:** colores, tipografías, tamaños, espaciados, tarjetas y botones comunes para que todas las pantallas se vean de la misma familia.
- **Móvil frente a escritorio**, con el mismo código:
  - En el móvil (y la app instalada): barra inferior, tarjetas a todo el ancho, botones grandes para el pulgar y respeto de las zonas del sistema (notch, barra de gestos).
  - En el ordenador: menú lateral, contenido en columnas y más datos a la vista.
  - Se detecta por el tamaño de pantalla y si la app está instalada.
- **Indicador «N» de Next.js** abajo a la izquierda: solo sale en modo desarrollo. Se oculta (`devIndicators: false`) y desaparecería del todo con una compilación de producción.

### M10 · Arquitectura de IA: mínimo LLM, máximo dato ⏳ (aprobado como plan; sin empezar)
Análisis del 2026-11-13. **Objetivo:** cada función resuelta con datos y reglas; el LLM solo para lo que de verdad lo necesita (texto libre, redactar). Que la app siga funcionando si la IA se encarece, se cae o hay que cambiar de proveedor.

- **Problemas detectados:**
  - **El agente gasta muchos tokens:**
    - Hace de 3 a 5 llamadas por pregunta y en cada una reenvía las 13 herramientas.
    - Guarda en el historial los resultados de las herramientas en bruto (hasta 12k caracteres).
    - Usa ids UUID.
  - **El LLM elige los ejercicios del plan** a partir de una lista enorme de nombres, sin tener en cuenta el perfil de deporte, la fatiga, el nivel ni el material.
  - **Los splits se piden al LLM** aunque se resuelven con plantillas.
  - **El conocimiento por deporte está en 4 sitios:** `training_prompt`, `sport_profiles`, `plan_stub` y alias repetidos.
  - **Los patrones se deducen por nombre en cada petición.**
  - **No se sabe qué material tiene el usuario.**
- **Decisiones:**
  - **Se queda:** Postgres como único almacén (el "grafo" de conocimiento va en tablas y arrays), Redis y Pydantic.
  - **No se adopta por ahora:** LangGraph, Neo4j, pgvector, LlamaIndex ni Pydantic AI.
  - **Cuándo revisar LangGraph:** si llegan flujos largos con pausas (plan de varias semanas que se reajusta) junto con cadenas de varios pasos de LLM, o tras pasar a la API de Anthropic.
  - **Los handlers serán funciones tipadas,** para poder convertirlos en nodos de un grafo sin reescribirlos.
- **Principios:**
  - **Coste de las consultas:** una consulta a Postgres cuesta ~1 ms y es coste fijo de servidor; una llamada al LLM cuesta segundos y dinero por uso.
  - **El LLM se usa al construir, no al ejecutar:** Claude ayuda a crear y revisar el mapeo de conocimiento (perfiles, etiquetas de ejercicios), que se guarda y se valida; en ejecución todo es determinista.
  - **Tareas de IA pequeñas y con salida cerrada,** para que las pueda hacer un modelo barato o local.
  - **El crítico de un plan es código** (un validador), no otro LLM.

| Fase | Entregable | Riesgo |
|---|---|---|
| F0 · Medir | Tokens, latencia y proveedor por tarea; tests en verde como punto de partida | Muy bajo |
| F1 · Contrato de IA | `AiTask` declarativo (esquema, nivel de modelo small/large, alternativa sin IA, máx. tokens); proveedor elegible por tarea | Bajo |
| F2 · Limpieza del agente | Historial sin resultados en bruto, ids cortos, herramientas por intención, router previo para consultas triviales | Bajo |
| F3 · Datos estructurados | Migración reversible: `patterns[]`, `equipment` y `level` en el catálogo; `users.equipment`; `injuries` estructurado; `goal_map` (objetivo → cualidades → patrones → zona) en los perfiles; `key_exercises` como ids; registro de deportes único | **Medio** (datos reales: copia de la BD antes) |
| F4 · Recomendador | Objetivo → candidatos (SQL) → filtros (material, nivel, lesiones) → ranking (carencias, prioridad, fatiga, familiaridad) → prescripción → explicación por plantilla. Incluye "no tengo este material" → alternativas con el material disponible. Endpoint, herramienta del agente y tarjeta en la UI | Bajo |
| F5 · Plan determinista | Ver abajo. Estado y versiones del plan en Postgres. Se retiran `plan_session.py`, `training_prompt`, `plan_stub` y `/plan/splits` **solo cuando el nuevo funcione igual o mejor** | **Medio** |
| F6 · API de Anthropic | Adaptador del SDK con tool use nativo y *prompt caching*, elegible por tarea; el CLI sigue para uso personal | Bajo (cuando haga falta) |

**Generador de planes determinista (F5):**
1. **Presupuesto de tiempo:** días de gimnasio × minutos → series por sesión (tiempo por serie = reps × ~3-4 s + descanso según la zona; + calentamiento y transiciones).
2. **Prioridades del usuario** (p. ej. atletismo: potencia de salto 5, fuerza de piernas 4, torso 1) → reparto de las series semanales por cualidad y patrón (`goal_map` + `pattern_targets` del perfil).
3. **Huecos por día:** potencia y pliometría al principio, sin cargar el mismo grupo en días seguidos ni la víspera del deporte (`load_rules`, `conflict_groups`).
4. **Ejercicios por puntuación** en cada hueco: encaje con el patrón, material, nivel, fatiga y recuperación, variedad y familiaridad.
5. **Prescripción** por zona (`rep_zones_by_phase`): potencia 3-5 reps explosivas con descansos largos, fuerza 3-6, hipertrofia 8-12…
6. **Validador:** series por músculo, ratio tirón/empuje y reglas de calendario. El LLM solo interviene, de forma opcional, para redactar la explicación o corregir si el validador falla, eligiendo entre candidatos ya filtrados.

**Antes de empezar:** commit de lo pendiente en `feature/refactor`, rama `feature/ai-architecture`, copia de la BD antes de F3, tests en verde y un commit por fase. Primer bloque propuesto: F0 + F1 + F2.

## 🗂️ Backlog (ideas para cuando la app esté en uso, después de M8)
Tu objetivo: que la IA te organice y te guíe sin tener que ser experto. Las mejoras saldrán de usar la app.

- **Completar los perfiles de deporte** (`data/sport_profiles/`): revisar el de boxeo con el uso real y añadir los deportes que practiques (running, escalada…). Proceso: Claude genera un borrador estructurado, se revisa y se valida automáticamente.
- **Feedback diario de recuperación para refinar la fatiga:**
  - "Hoy me noto descansado / sigo cansado" y las agujetas por músculo al día siguiente de entrenar.
  - Ya existe la base: readiness diaria, mapa corporal de agujetas (`daily_muscle_doms`) y calibración personal (`user_muscle_calibration`). Falta preguntarte de forma proactiva (por ejemplo, el agente o una notificación tras cada entreno) y usar tus respuestas para ajustar automáticamente las constantes de recuperación por músculo.
- **Fatiga que aprende:** comparar lo que predice el modelo con lo que reportas y corregir τ y pesos con el tiempo (ADR-005, consecuencias).
- **HTTPS local con mkcert** (`dev-up.ps1 -Https` ya preparado): escanear códigos de barras con la cámara, instalar la PWA a pantalla completa y mantener la pantalla encendida durante el entreno. Pasos: `winget install FiloSottile.mkcert`, `mkcert -install` y poner `rootCA.pem` en el móvil.
- **CrossFit / Hyrox** (propuesta de arquitectura):
  - **Modelo de WOD:** `details.wod = {format: amrap|emom|for_time|rounds|intervals, timeCapS, rounds, result (tiempo, rondas+reps), blocks:[{station|exercise, reps|distanceM|calories, weightKg}]}`, dentro de `training_session` con `discipline = crossfit|hyrox`.
  - **Catálogo:** añadir las estaciones (SkiErg, remo, sled push/pull, burpee broad jump, farmers carry, sandbag lunges, wall balls, carrera de 1 km) y los movimientos de CrossFit (thruster, toes-to-bar, double unders…), con su `muscleMap`.
  - **Fatiga:** cada bloque carga sus músculos como en el gimnasio (volumen relativo × implicación), y la parte de carrera o ergómetro por TRIMP o duración, igual que el resto de deportes. Sin reglas nuevas en el motor: solo datos.
  - **Perfil de deporte:** `data/sport_profiles/hyrox.json` y `crossfit.json` (cualidades, test de referencia, semana tipo) para el agente y la preparación.
  - **IA:** el parser y el agente reconocen el formato del WOD a partir del texto ("AMRAP 12: 10 wall balls, 10 burpees") y proponen el registro para que lo confirmes, como hoy.
- **Fase de temporada y calendario de combate** en tu perfil, para que los objetivos cambien solos (precompetición, descarga).

## Dependencias

```
M0 ─► M1 (gym) ─► M3 ─► M6
  └─► M2 (IA) ─► M4 ─► M5
M4 ─► M4.1 (mejoras) ─► M5 (comidas) ─► M5.1 (prueba en el móvil) ─► M6.1/M6.2 ─► M7 ─► M8 ─► M6.3
M1..M6 ─► M7 ─► M8
```
M1 solo usa el LLM para traducir las instrucciones (un lote único). Si M2 no está listo, se hace con el CLI a mano.

## Siguiente paso
**Uso real**: crear tu usuario, instalar la app en el móvil (sección 10 de tu guía) y entrenar con ella. Después, pulido con lo que salga del uso, el backlog y M6.3.
