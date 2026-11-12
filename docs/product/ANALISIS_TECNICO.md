# Análisis técnico: modelos de cálculo, conocimiento por deporte e integraciones

> ✅ §2 (fatiga), §3 (1RM) y §5 (registro de deporte) aplicados en M4.1: ver [ADR-005](decisions/ADR-005-fatiga-1rm-registro-deporte.md).

> 2026-11-12 · Revisión de los cálculos que heredamos de OpenCode (fatiga, 1RM, kcal), de cómo se gestiona cada deporte, y estudio de nutrición y Strava/Garmin. Sirve de base para el hito **M4.1 · Mejoras encontradas** del [ROADMAP](ROADMAP.md).

## 1. Resumen

| Área | Estado | Veredicto |
| :-- | :-- | :-- |
| Fatiga | Modelo impulso-respuesta por grupo muscular | 🔴 **Dos errores de fondo**: el gym ignora los ejercicios y la recuperación es demasiado rápida |
| 1RM / fuerza | Epley, duplicado en dos sitios | 🟡 Correcto pero mejorable (RPE/RIR, progresión) |
| Kcal | MET + RPE + FC; gym con trabajo mecánico | 🟡 Razonable, con doble conteo de intensidad |
| Conocimiento por deporte | Reglas + 5 prompts genéricos + perfil de boxeo en código | 🟡 No es "100 % IA", pero está disperso en 3 sitios |
| Nutrición | No existe | Ver §6 |
| Strava/Garmin | No existe | Ver §7 |

La app **no recalcula con IA las necesidades de cada deporte**. Casi todo son reglas deterministas y la IA solo interpreta texto, redacta y conversa. El problema es que ese conocimiento está repartido en tres sitios sin una fuente común (§5).

---

## 2. Fatiga muscular

### Cómo funciona hoy (`analytics/fatigue.py`)
Para cada uno de los 12 grupos musculares y cada día:

```
F(d) = A · F(d-1) + I(d)                       estado de fatiga 0-100
A    = 0.30·e^(-m/0.5) + 0.70·e^(-m/3)         factor de recuperación diario
I    = 100 · peso_disciplina[grupo] · V_rel · (RPE/10)
```

- **Peso por disciplina:** tabla `discipline_muscle_load`. Por ejemplo, en boxeo: hombros 0,9, core 0,85…
- **V_rel:** volumen relativo, con tope 1,0.
  - Boxeo: golpes equivalentes / 2000 (desde M3, por bloques).
  - Running: km / 10 (con pendiente).
  - Ciclismo: km / 40; natación: km / 2,5.
  - Gym: kg totales de la sesión / 15.000.
  - Resto: minutos / 90.
- **m (modulador):** se calcula con el sueño, las agujetas (DOMS) del mapa corporal y los días de descanso. Hay ganchos para HRV y nutrición, aún sin datos.
- **Calibración personal:** ajusta pesos y `tau2` por grupo según tu feedback.
- **ACWR:** carga aguda (7 días) / crónica (28 días). Avisa si pasa de 1,5.

### Problemas detectados

**P1 · El gym no usa los ejercicios realizados (grave).** La carga de una sesión de gym reparte el volumen total con pesos fijos de "gym" (pecho 0,80, espalda 0,75, cuádriceps 0,65…). Medido con el código actual, un **día de pierna de 12.000 kg deja más fatiga en el pecho (51) que en los cuádriceps (42)**. La app ya sabe qué músculos trabaja cada ejercicio (`muscle_map` del catálogo y `compute_muscle_impacts`), pero la fatiga no lo usa.

**P2 · La "doble exponencial" no funciona como tal.** Las dos exponenciales (aguda de 12 h y daño muscular de 3 días) se suman en **un único factor diario** que multiplica todo el estado. En la práctica es una sola exponencial con **vida media de unas 27 h**: a los 3 días queda el 16 %. La intención (que el daño muscular dure unas 72 h) se pierde. Un modelo de dos compartimentos necesita dos estados por grupo (agudo y residual), cada uno con su constante.

**P3 · Todos los grupos se recuperan al mismo ritmo.** Cuádriceps, isquios y espalda (masa grande, contracción excéntrica) se recuperan más despacio que bíceps o gemelos. Solo la calibración personal lo matiza.

**P4 · Saturación y referencias arbitrarias.** El tope de V_rel en 1,0 hace que una sesión enorme y una grande cuenten igual. Las referencias (2000 golpes, 15.000 kg) no están justificadas.

**P5 · Deportes "genéricos" solo por minutos.** Fútbol, tenis o escalada cargan lo mismo con independencia del contenido. Además, los bloques de combate (M3) dan volumen, pero no cambian qué músculos cargan: la comba debería cargar gemelos y el saco, hombros.

### Propuesta
1. **Carga de gym por músculo a partir de las series reales:**
   - Para cada serie de trabajo: `activación[ejercicio][grupo] × esfuerzo(RPE/RIR, reps)`.
   - Normalizar por una referencia de series por sesión, del orden de 8-10 series efectivas por grupo para V_rel = 1.
   - Corrige P1 y aprovecha el catálogo y el RPE por serie.
2. **Modelo de dos compartimentos real:** estado agudo (τ≈0,5 d) y residual (τ≈2-3 d) por grupo, cada uno con su factor. La fatiga mostrada es la suma.
3. **τ por grupo:** grande o excéntrico (cuádriceps, isquios, glúteos, espalda) más lento; pequeño (bíceps, tríceps, gemelos, antebrazo) más rápido. La calibración personal se mantiene encima.
4. **Pesos musculares por tipo de bloque** (comba → gemelos y hombros; saco → hombros, core y tríceps; sparring → todo y cuello), definidos en el registro de deporte (§5).
5. **Sustituir el tope duro** por una curva saturante, por ejemplo `1 - e^(-V/ref)`, para que más volumen siga sumando con rendimiento decreciente.
6. **Validación:** comparar la predicción con las agujetas que reportas (la tabla `daily_muscle_doms` ya existe) para ajustar constantes con datos.

---

## 3. 1RM y progresión de fuerza

**Hoy:**
- **1RM estimado con Epley** (`peso × (1 + reps/30)`) en dos sitios:
  - `analytics/records.py` (M1) lo limita a 1-12 reps.
  - `analytics/computations.est_1rm` (OpenCode) **no tiene límite**: con 30 reps estima el doble del peso, lo que distorsiona las estadísticas de progreso.
- **Sugerencia de peso** (`weight_suggestion.py`): **repite el último peso** usado. No progresa.

**Propuesta:**
1. Una única función de 1RM.
   - Con RPE o RIR registrado, usar la tabla RPE→% de 1RM (Zourdos/Helms), más fiable que Epley en series no máximas.
   - Sin RPE, Epley hasta 10 reps y no estimar por encima de 12.
2. **Progresión sugerida** (pendiente de M1):
   - Doble progresión: si se completan todas las series en la parte alta del rango, subir +2,5 kg (tren superior) o +5 kg (inferior); si no, mantener.
   - O autorregulación por RPE objetivo de la rutina.
3. Detectar estancamiento: 1RM estimado plano 3-4 semanas → proponer variación (lo hace el recomendador de M4).

---

## 4. Calorías

**Hoy** (`analytics/kcal.py`):
- **Deportes:** MET de la disciplina × peso × horas × factor RPE (0,6-1,6) × factor FC.
- **Gym:** trabajo mecánico (kg × reps × recorrido) / eficiencia 22 %, más coste metabólico por minuto y EPOC, modulado por los descansos.
- Devuelve un margen de ±15 % y un nivel de confianza.

**Problemas:**
- El MET ya representa una intensidad típica: multiplicarlo además por un factor RPE de hasta 1,6 **cuenta la intensidad dos veces**.
- El factor de FC no conoce tu FC máxima ni tu edad.

**Propuesta:**
1. Si hay FC media, usar una ecuación por FC (Keytel et al., con sexo, edad, peso y FC), mucho más precisa que MET.
2. Sin FC, elegir el MET por subtipo e intensidad (Compendium: saco frente a sparring frente a técnica; rodaje frente a series) usando los bloques de M3, en vez de multiplicar por el RPE.
3. El gasto diario alimentará el balance de nutrición (§6).

---

## 5. Conocimiento por deporte: de reglas dispersas a un registro único

### Cómo se gestiona hoy cada deporte

| Dónde | Qué guarda | Lo usa |
| :-- | :-- | :-- |
| Tabla `discipline` (22) | Nombre, MET, categoría, tipo cardio/fuerza | kcal, UI |
| Tabla `discipline_muscle_load` | Peso de carga por grupo muscular | Fatiga |
| Tabla `training_prompt` (5 perfiles en texto) + `discipline_training_prompt` | Prompts genéricos por cualidad: equilibrada, fuerza, **explosividad** (boxeo, artes marciales, fútbol…), hipertrofia, resistencia | Generación de planes (LLM) |
| `analytics/sport_analysis.py` (M4, código) | Perfil estructurado del **boxeo**: patrones, músculos, zonas de reps, conflictos | Analizador, agente |

Así que no es "100 % IA", pero:
- El boxeo está descrito **dos veces** de forma distinta: el prompt "explosividad" (unos 1.200 tokens, compartido con voleibol o tenis) y el perfil estructurado.
- Cada vez que se genera un plan se envían unos 1.200 tokens de prompt genérico que no son específicos del boxeo.
- Añadir un deporte exige tocar tres sitios.

### Propuesta: registro de conocimiento por deporte
Una sola fuente estructurada y versionada por deporte: `data/sport_profiles/<deporte>.json`, validada con pydantic y cargada en la tabla `sport_profile`. Cada perfil contiene:

- **Cualidades** con prioridad: potencia, resistencia a la potencia, fuerza, resistencia aeróbica, movilidad…
- **Sistemas energéticos** y formato típico: rounds 3×3', descansos de 1'…
- **Patrones** con series objetivo y **ejercicios clave** por patrón.
- **Rangos de series por músculo** y **zonas de reps por fase**: pretemporada, específico, precompetición, descarga.
- **Pesos de carga muscular por tipo de bloque**, que necesita la fatiga (§2.4).
- **Riesgos y lesiones típicas, con prehab**: hombro, cuello y muñeca en boxeo.
- **Reglas de calendario:** qué no machacar la víspera, separación mínima entre gym y sparring.
- **Notas de periodización**, en texto breve para el LLM.

**Quién lo consume:**
1. **Analizador** (M4): ya usa un perfil así, solo cambia de dónde lo lee.
2. **Fatiga:** pesos por bloque y τ por grupo.
3. **Planificador y prompts:** se genera un **resumen compacto (unos 250-400 tokens)** del perfil del deporte. Sustituye al prompt genérico de 1.200 tokens y es específico.
4. **Agente:** una herramienta `perfil_deporte` devuelve el perfil cuando hace falta, en vez de que el LLM "razone" qué necesita el boxeo.

**Cómo se crean los perfiles:** una sola vez, offline, con Claude (como la traducción del catálogo), y después **se revisan a mano** y se versionan en el repo. Coste en tiempo de ejecución: **0 tokens** para saber qué necesita cada deporte. La IA solo personaliza: tu fase, tus lesiones, tu calendario.

**Capa personal encima del perfil:**
- `user_sport_profile`: deporte principal, fase actual y fecha de combate, nivel, lesiones y ajustes.
- La fase cambia los objetivos. A 4 semanas de un combate: menos volumen, más potencia y más trabajo específico.

**Ahorro estimado:**
- Por plan generado, de unos 1.200 tokens de prompt genérico a unos 300 de perfil compacto.
- Sin llamadas extra para deducir necesidades.
- Y, si se pasa a la API de Anthropic, el perfil va en el prefijo estable del prompt y se beneficia del **prompt caching**.

---

## 6. Nutrición (RF-05)

> Investigación web del 2026-11-11. Lo marcado con ⚠️ no se pudo confirmar en una fuente oficial: hay que revisarlo antes de decidir.

| Fuente | Coste | Productos de España / español | Código de barras | Lenguaje natural | Licencia |
| :-- | :-- | :-- | :-- | :-- | :-- |
| **Open Food Facts** | Gratis (1 llamada = 1 escaneo real; exportaciones diarias para volumen) | ✅ Buena en marcas de España y la UE (colaborativa, calidad variable) | ✅ Su punto fuerte | ❌ | ODbL: atribución; una base derivada pública hereda ODbL |
| **USDA FoodData Central** | Gratis, 1.000 peticiones/h | ❌ En inglés y de EE. UU.; vale para alimentos genéricos | Solo EE. UU. | ❌ | CC0 |
| **FatSecret Platform** | Basic gratis (5.000/día, **solo dataset de EE. UU.**); Premier Free para startups; Premier de pago para más de 60 países | ⚠️ Fuera de EE. UU. solo en Premier | ✅ | Complemento de pago | Atribución en los planes gratuitos |
| **Edamam** | Desde unos 14 $/mes ⚠️ | ⚠️ Centrada en EE. UU. | ✅ | ✅ | La caché solo en algunos planes |
| **Nutritionix** | Precios no públicos (ahora es de Syndigo) | ❌ | ✅ | ✅ | No recomendada |
| **BEDCA (AESAN)** | Sin API; el uso electrónico requiere permiso | ✅ Alimentos genéricos españoles | ❌ | ❌ | Pedir autorización |

**Recomendación:**
- **Ahora (uso personal):**
  - Open Food Facts para el código de barras y los productos de marca.
  - USDA para alimentos genéricos (huevo, arroz, pollo).
  - **Claude**, que ya tenemos, para el lenguaje natural ("2 huevos y una tostada" → lista de alimentos con gramos), buscando cada alimento en esas bases.
  - Se evita así pagar el complemento de lenguaje natural de FatSecret o Edamam.
- **App pública pequeña:** lo mismo, guardando en nuestra BD lo que el usuario confirma (respetando ODbL). Si hacen falta datos de España con licencia comercial clara: FatSecret Premier (presupuesto) o BEDCA con autorización de AESAN.

**Modelo propuesto:**
- `food`: caché local con fuente e id externo, por 100 g: kcal, proteína, hidratos, grasa y fibra.
- `meal_entry`: fecha, comida (desayuno…), alimento, gramos y **copia de los macros** en el momento del registro.
- `nutrition_target`:
  - Gasto basal por Mifflin-St Jeor.
  - Más el gasto de los entrenos (`kcal.py`).
  - Más el objetivo (déficit, mantenimiento o superávit).
  - Proteína en g/kg según la fase.
- El agente añade la herramienta "registrar comida", que propone y requiere confirmación, igual que los entrenos.
- El balance diario va en el dashboard. Para boxeo es útil el **control de peso hacia la categoría** antes de un combate.

---

## 7. Strava / Garmin (RF-07)

### Strava: ⚠️ conflicto con la IA de la app
- **Acuerdo de la API (desde noviembre de 2024, endurecido en 2026):**
  - Prohíbe usar los datos de la API para entrenar modelos de IA.
  - Según la lectura de Terra (agregador), prohíbe también usarlos en **aplicaciones de IA (prompts, RAG)**, incluso derivados.
  - Las apps solo pueden mostrar los datos de un usuario a ese mismo usuario.
  - ⚠️ Hay que leer el acuerdo oficial y, si hace falta, pedir aclaración por escrito.
- **Desde junio de 2026** el desarrollador necesita **suscripción de Strava** (unos 12 $/mes ⚠️).
- **Capacidad:** una app nueva empieza con 1 atleta; sube a 10 sin revisión.
- **Límites:** 200 peticiones/15 min y 2.000/día.
- **Técnica:** OAuth2 (`activity:read_all`). Una suscripción de webhook por app; el aviso solo trae el id, el callback debe responder en menos de 2 s y después se pide la actividad. Hay streams de FC, ritmo y GPS.

Tu app **pasa los datos al LLM** (agente, análisis, fatiga explicada), así que Strava encaja mal: habría que aislar sus datos de cualquier prompt, lo que le quita la mitad del valor.

### Garmin: mejor camino para tu caso
| Vía | Estado | Para nosotros |
| :-- | :-- | :-- |
| **Clave personal de la API oficial** (ajustes de la cuenta, reabierta en octubre de 2026 ⚠️) | Solo lectura de **tus** datos: actividades en JSON y FIT, salud en JSON | ✅ **Recomendada ahora** |
| Programa oficial Starter/Enterprise | Requiere aprobación, web pública y política de privacidad | Para cuando haya más usuarios |
| **Importar archivos FIT** exportados | Estable y sin riesgo de ToS | ✅ Plan B inmediato, también para otros relojes |
| `python-garminconnect` (no oficial) | Se rompió en marzo de 2026 por cambios del SSO | ❌ Frágil |
| **Health Connect (Android) / HealthKit (iOS)** | Garmin escribe actividades y FC en Health Connect | ✅ Con la app nativa (M8) es el agregador natural (Garmin, Polar, Samsung…) |
| Terra API | Desde unos 399 $/mes | ❌ Demasiado caro para este caso |

### Diseño de la importación (común a todas las fuentes)
- `external_account`: proveedor, tokens cifrados con refresh y estado.
- `training_sessions.external_source` + `external_id` (único) para no duplicar. Además, un control de solapamiento horario con sesiones registradas a mano.
- **Ingesta asíncrona:** webhook o sondeo → cola Redis (el worker ya existe) → mapeo a la disciplina y a las métricas de resistencia de M3. La FC y el desnivel alimentan las kcal (Keytel, §4) y la fatiga.
- **Parser de FIT** (librería `fitparse` o `fitdecode`): sirve para el FIT de Garmin, para la importación manual y para otros relojes.

**Recomendación:**
1. **M6 = Garmin** (clave personal + importación FIT), no Strava.
2. Strava solo si confirmas por escrito que su uso con el LLM está permitido, o aislando sus datos de la IA.
3. Health Connect y HealthKit cuando exista la app nativa (M8).

---

## 8. Otras cosas hechas que conviene mejorar

| # | Qué | Por qué | Esfuerzo |
| :-- | :-- | :-- | :-- |
| 1 | `computations.est_1rm` sin límite de reps, duplicado con `records.estimated_1rm` | Estadísticas de progreso infladas | Bajo |
| 2 | La sugerencia de peso repite el último peso | No hay progresión | Bajo-medio |
| 3 | `chat/plan_session.py` (1038 líneas de regex y estados) | Lo sustituye el agente; mantenimiento caro | Medio (retirar) |
| 4 | Tabla `exercises` (modelo antiguo) en sesiones no-gym antiguas | Dos modelos en las estadísticas (ADR-001) | Medio |
| 5 | `web/lib/routineReview.ts`: análisis de rutina en el cliente | Duplica el backend (M4) | Bajo (tras tu merge) |
| 6 | Latencia del agente (8-15 s) | Un proceso de CLI por paso | Medio: API de Anthropic con tool use nativo + streaming (M7) |
| 7 | Sesiones mixtas con una sola disciplina | Una clase de boxeo con pesas pierde la parte de fuerza | Medio |
| 8 | Imágenes del catálogo servidas desde GitHub | Sin red en el gym no hay imágenes | Bajo (descargar al repo o a caché PWA) |

---

## 9. Propuesta de orden

1. **M4.1 · Mejoras encontradas** (antes de añadir más funciones, porque todo lo demás se apoya aquí):
   - Fatiga por series reales y dos compartimentos (P1-P3).
   - Unificar el 1RM y la progresión sugerida.
   - Registro de conocimiento por deporte con el boxeo como primer perfil, y migrar los prompts.
2. **M5 · Nutrición** y **M6 · Strava** (independientes).
3. **M7 · Blindaje** antes de exponer la app a internet; **M8 · App móvil**.
