# Diseño de la interfaz: estándares, diagnóstico y propuesta

> Estado: **aprobada** (M9, punto 3); en implementación por fases. Fecha: 2026-11-12.
> Objetivo: una app cómoda en el móvil (uso principal, en el gimnasio y en el día a día) que también se vea bien en el ordenador, con el mismo código.

---

## 1. Qué dicen los estándares de una app funcional

Referencias: Material Design 3 (Google/Android), Human Interface Guidelines (Apple), WCAG 2.2 (accesibilidad) y las 10 heurísticas de usabilidad de Nielsen.

### 1.1 Navegación
| Regla | De dónde sale | Qué implica para nosotros |
|---|---|---|
| **3 a 5 destinos principales** en una barra inferior en el móvil. Siempre visibles, con icono y texto. | Material 3 *Navigation bar*, Apple *Tab bar* | Mantener 5 pestañas, pero que cada una sea un «mundo» completo. |
| **El tamaño de pantalla decide el tipo de menú.** Compacto (< 600 px): barra inferior. Medio (600-840 px): *navigation rail* (columna de iconos a la izquierda). Expandido (> 840 px): menú lateral. | Material 3 *Window size classes* | Hoy solo hay diseño de móvil; en el ordenador se ve un móvil estirado. |
| **Dentro de una pestaña**, las secciones van como **pestañas superiores o segmentos**, no como pantallas sueltas con enlaces. | Material 3 *Tabs* / *Segmented buttons* | Progreso tiene 5 pantallas sueltas: pasan a ser segmentos de una sola. |
| **La cuenta y los ajustes van en la barra superior** (avatar a la derecha), no flotando sobre el contenido. | Material 3 *Top app bar*, Apple HIG | Corrige el choque del avatar con el botón del chat. |
| **Una acción principal por pantalla** (botón destacado o FAB): «Empezar entreno», «Añadir comida». | Material 3 *FAB* | Lo importante, a un toque y en la zona del pulgar. |
| **Atrás predecible:** las subpantallas tienen flecha atrás en la barra superior; el botón atrás de Android hace lo mismo. | Apple HIG, Nielsen (control del usuario) | Hoy cada pantalla resuelve la vuelta a su manera. |

### 1.2 Contenido y densidad
- **Revelación progresiva:** primero el dato clave y después el detalle al tocar («ver más», desplegables, hojas inferiores). Una tarjeta = una idea = un número grande + una frase.
- **Jerarquía visual:** en cada pantalla, un elemento domina; los demás acompañan. Si todo está igual de destacado, nada lo está.
- **Menos texto:** etiquetas cortas, iconos coherentes y gráficos simples. Las explicaciones largas, en «¿qué es esto?» (tooltip u hoja).
- **Estados completos:** cada lista o gráfico tiene estado vacío (con una acción para empezar), de carga (esqueleto) y de error (con reintentar).

### 1.3 Ergonomía en el móvil
- **Zona del pulgar:** las acciones frecuentes, en la mitad inferior. Arriba, solo lo que se consulta.
- **Tamaño táctil mínimo:** 48 × 48 px (Material) / 44 pt (Apple). Nunca por debajo de 24 px (WCAG 2.2, 2.5.8).
- **Zonas seguras:** respetar el notch y la barra de gestos (`env(safe-area-inset-*)`), sobre todo con la app instalada a pantalla completa.
- **Formularios:** teclado adecuado a cada campo (numérico para pesos y repeticiones), botones grandes y sin escritura cuando se pueda elegir (chips, pasos +/-).

### 1.4 Sistema visual
- **Tokens de diseño:** colores por función (primario, superficie, éxito, aviso, peligro), una escala tipográfica (título, encabezado, cuerpo, etiqueta), espaciados en múltiplos de 4/8 px, radios y sombras definidos una vez y reutilizados.
- **Contraste:** al menos 4,5:1 en el texto y 3:1 en iconos y bordes de controles (WCAG AA). Con tema oscuro y claro.
- **Componentes comunes:** barra superior, barra inferior, rail, tarjeta, elemento de lista, chip, segmentos, hoja inferior, botón (primario, secundario, texto), FAB, estado vacío, esqueleto y aviso tipo *toast*.
- **Movimiento:** transiciones cortas (150-250 ms) que expliquen de dónde viene cada cosa. Nada decorativo durante un entreno.

---

## 2. Diagnóstico de la app actual

| # | Problema | Estándar que incumple | Impacto |
|---|---|---|---|
| 1 | **El avatar flota y choca con el botón del chat** en la app instalada. | Barra superior / zonas seguras | Alto: se toca lo que no es. |
| 2 | **Progreso son 5 pantallas sueltas** (Historial, Fatiga, Preparación, Carga y análisis, Peso) con información que se repite: la fatiga sale en Inicio, en Fatiga y en Análisis. | Pestañas superiores, revelación progresiva | Alto: cuesta encontrar las cosas y hay mucho dato. |
| 3 | **El Inicio tiene 7-8 bloques** del mismo peso visual. | Jerarquía, densidad | Medio-alto. |
| 4 | **Perfil, Objetivos y Configuración son 3 pantallas** que se solapan (datos personales, metas, cuenta, Garmin, tema). | Agrupación lógica (Nielsen) | Medio. |
| 5 | **No hay diseño para el ordenador:** el móvil se estira. | *Window size classes* | Medio, porque se usa sobre todo en el móvil. |
| 6 | **El CSS tiene 3.100 líneas en un único archivo**, con clases sueltas por pantalla y dos paletas. Cada pantalla tiene márgenes, títulos y botones algo distintos. | Sistema de diseño | Alto a largo plazo: es la razón de la «falta de unidad». |
| 7 | **No hay acción principal clara** en Entrenar ni en Comidas. | FAB / una acción principal | Medio. |
| 8 | **No se respetan las zonas seguras**, y el indicador «N» de Next sale en desarrollo. | Zonas seguras | Bajo-medio. |
| 9 | **Estados vacíos, de carga y de error desiguales** (unos con texto, otros vacíos). | Estados completos | Medio. |

---

## 3. Inventario de pantallas (hoy)

**Frecuencia de uso prevista:** A = a diario, B = semanal, C = ocasional.

| Pantalla (ruta) | Qué hace hoy | Frec. |
|---|---|---|
| Login (`/`) · Registro (`/registro`) | Entrar y crear cuenta | C |
| **Inicio** (`/dashboard`) | Saludo, meta, «Saca más partido», avisos, preparación, mapa de fatiga, semana, comida de hoy, actividad reciente | A |
| **Entrenar** (`/entrenar`) | Empezar gimnasio (plantillas) y 4 accesos | A |
| Entreno en curso (en `/entrenar`) | Series, descanso, añadir ejercicio, terminar y resumen | A |
| Registrar actividad (`/registrar`) | Texto libre o formulario para otros deportes | B |
| Importar (`/importar`) | Subir FIT, GPX o TCX | C |
| Rutinas (`/rutinas`) | Lista, editar, evaluar y analizar | B |
| Ejercicios (`/ejercicios`) · ficha (`/ejercicios/[id]`) | Catálogo, filtros, detalle, historial y alternativas | B |
| **Comidas** (`/comidas`) | Día, comidas por momento, añadir (buscar, código, rápido, IA, plantillas), objetivo y peso | A |
| **Progreso** (`/progreso`) | Avance semanal y 5 accesos | B |
| Historial (`/entrenos`) · detalle (`/entrenos/[id]`) | Lista por periodo, gráficos y detalle con mapa, FC y fatiga | B |
| Fatiga (`/fatiga`) | Mapa, readiness, señales y por grupo | A/B |
| Preparación (`/preparacion`) | Puntuación, carencias, patrones, músculos y zonas | B |
| Carga y análisis (`/analisis`) | Fatiga media/pico y carga por grupo | C |
| **Coach** (`/chat`) | Conversación con propuestas que se confirman | A/B |
| Perfil (`/perfil`) | Datos físicos, kcal, cambiar email y contraseña | C |
| Objetivos y deporte (`/objetivos`) | Deporte principal, otros deportes y metas | C |
| Configuración (`/configuracion`) | Instalar app, Garmin, cuenta y seguridad, tema | C |
| *Modales* | Bienvenida, añadir comida, objetivo de nutrición, editar rutina, análisis de rutina, explicar fatiga, crear ejercicio… | — |

---

## 4. Propuesta: nueva organización

### 4.1 Mapa de navegación
```
BARRA INFERIOR (móvil) / RAIL o MENÚ LATERAL (tablet y ordenador)
┌──────────┬──────────────┬─────────────┬──────────────┬──────────┐
│   Hoy    │   Entrenar   │   Comidas   │   Progreso   │  Coach   │
└──────────┴──────────────┴─────────────┴──────────────┴──────────┘
Barra superior en cada pestaña: título · [acción contextual] · avatar (cuenta)

Hoy           → resumen del día (sin subsecciones)
Entrenar      → [Empezar entreno] + segmentos: Rutinas | Ejercicios | Historial
                acciones: Registrar otra actividad · Importar archivo
Comidas       → segmentos: Día | Semana | Peso y objetivo     FAB: Añadir comida
Progreso      → segmentos: Resumen | Fatiga | Rendimiento | Cuerpo
Coach         → chat
Avatar        → Cuenta: Perfil y objetivos · Conexiones (Garmin) · App (tema, instalar) · Seguridad
```

**Cambios clave:**
- **El avatar pasa a la barra superior** (estándar): se acaba el choque con el chat. El Coach queda como pestaña y no hace falta botón flotante.
- **Progreso pasa de 5 pantallas a 1 con 4 segmentos:**
  - **Resumen:** cómo avanzas.
  - **Fatiga:** mapa, readiness y señales.
  - **Rendimiento:** preparación para tu deporte + carga.
  - **Cuerpo:** peso y composición.
- **El Historial pasa a Entrenar**, porque es «mis entrenos». En Progreso quedan las tendencias.
- **Perfil, Objetivos y Configuración se unen en «Cuenta»**, con secciones claras.
- **Acción principal visible:** «Empezar entreno» en Entrenar y «Añadir comida» en Comidas, en la zona del pulgar.

### 4.2 Pantalla por pantalla

**Hoy**
- Objetivo: responder en 5 segundos a «¿qué hago hoy y cómo voy?».
- Orden:
  1. Saludo + meta principal (cuenta atrás), en una línea.
  2. **Una tarjeta «Hoy»**: recomendación del día a partir de los avisos (entrenar, suave o descanso) y botón «Empezar entreno».
  3. Cuerpo: mapa de fatiga compacto (tocar → Progreso › Fatiga).
  4. Comida: anillo de kcal y barra de proteína (tocar → Comidas).
  5. Semana: puntos de días activos y minutos por deporte.
  6. Último entreno (uno; «ver todos» → Entrenar › Historial).
- Pasan a segundo plano: «Saca más partido» (banner que se cierra) y la puntuación de preparación (en Progreso › Rendimiento, con un aviso en Hoy si es baja).

**Entrenar**
- Arriba, el botón grande **«Empezar entreno»** (con la rutina del día sugerida) y debajo los segmentos *Rutinas | Ejercicios | Historial*.
- En la barra superior, menú «+»: Registrar otra actividad e Importar archivo.
- **Entreno en curso:** pantalla completa sin barra inferior (modo foco), botones grandes, temporizador de descanso fijo abajo y pantalla siempre encendida.

**Comidas**
- **Día:** fecha con flechas, anillo de kcal y macros arriba, y las comidas del día como lista (desayuno…cena) con «+» en cada una.
- **FAB «Añadir»:** hoja con buscar (primero tus frecuentes), código de barras, rápido y describir con IA.
- **Semana:** medias y tendencia. **Peso y objetivo:** registro de peso, gráfico y objetivo nutricional.

**Progreso**
- **Resumen:** semana actual frente a la anterior, constancia (racha) y avances (1RM, ritmos).
- **Fatiga:** el cuerpo grande, readiness y señales; el detalle por grupo, plegado.
- **Rendimiento:** preparación para tu deporte (puntuación + qué mejorar) y carga (monotonía, ACWR), con «¿qué es esto?».
- **Cuerpo:** peso y su tendencia frente a la meta.

**Coach**
- Chat a pantalla completa con sugerencias rápidas («¿qué entreno hoy?», «analiza mi semana») y propuestas como tarjetas confirmables.

**Cuenta** (desde el avatar)
- **Perfil y objetivos:** datos físicos, deporte principal y metas.
- **Conexiones:** Garmin.
- **App:** instalar y tema.
- **Seguridad:** sesiones, datos y borrar cuenta.
- También email y contraseña.

### 4.3 Móvil frente a ordenador (mismo código)
| | Móvil (< 600 px) y app instalada | Tablet (600-1024 px) | Ordenador (> 1024 px) |
|---|---|---|---|
| Menú | Barra inferior de 5 | Rail de iconos a la izquierda | Menú lateral con textos y avatar abajo |
| Contenido | Una columna, tarjetas a todo el ancho | 1-2 columnas | Rejilla de 2-3 columnas; Hoy y Progreso en paneles |
| Listas con detalle (historial, rutinas, ejercicios) | Lista → pantalla de detalle | Lista → detalle | **Lista y detalle lado a lado** |
| Hojas (añadir comida…) | Hoja inferior | Hoja inferior | Diálogo centrado |
| Entreno en curso | Pantalla completa | Pantalla completa | Panel central ancho |

La app detecta el ancho de pantalla y si está instalada (`display-mode: standalone`), y usa los mismos componentes con distinta disposición.

---

## 5. Sistema de diseño propuesto

- **Color (tema oscuro por defecto y claro opcional):**
  - **Fondo y superficies** en 3 niveles: fondo, tarjeta y tarjeta elevada.
  - **Colores de marca:**
    - **Primario**, un solo color de marca para acciones y selección.
    - **Secundario** solo para datos positivos.
  - **Colores de estado:**
    - **Avisos:** éxito (verde), aviso (ámbar), peligro (rojo).
    - **Escala de fatiga:** verde → ámbar → rojo, la misma en toda la app.
    - **Colores por deporte**, fijos (gimnasio, carrera, bici, natación, combate).
- **Tipografía:** una familia para todo (Inter) más una de titulares para números grandes (Barlow Condensed, ya cargada). Escala: 32 / 24 / 20 / 16 / 14 / 12 px.
- **Espaciado:** 4 · 8 · 12 · 16 · 24 · 32 px. Margen lateral de pantalla: 16 px en el móvil y 24-32 px en el ordenador.
- **Forma:** radio de 12 px en tarjetas y hojas, 999 px en chips y botones redondeados. Sombras solo en elementos elevados (hojas, FAB).
- **Iconos:** lucide, trazo 1,75 y tamaños 20/24 px. Siempre con texto en la navegación.
- **Componentes base (una sola versión de cada uno):**
  - **Estructura:** `AppShell` (decide barra, rail o menú), `TopAppBar`, `BottomNav`/`NavRail`, `Segmented`.
  - **Contenido:** `Card`, `StatTile` (número grande + etiqueta), `ListItem`.
  - **Interacción:** `Sheet` (hoja/diálogo), `Button` (primario, secundario, texto, peligro), `Fab`, `Chip`.
  - **Estados:** `EmptyState`, `Skeleton`, `Toast`.
- **Organización del código:** tokens en `styles/tokens.css`, componentes con su CSS al lado (CSS Modules) y el `globals.css` actual adelgazando pantalla a pantalla.

---

## 6. Plan de implementación (por fases, cada una usable)

| Fase | Contenido | Resultado visible |
|---|---|---|
| **F1 · Base** | Tokens; `AppShell` adaptable (barra inferior, rail o menú lateral); `TopAppBar` con avatar; zonas seguras; ocultar el indicador de Next; componentes base | Se acaba el choque del avatar; menú correcto en móvil y ordenador |
| **F2 · Reorganización** | Progreso con segmentos; Historial en Entrenar; Cuenta unificada; redirecciones desde las rutas antiguas | Menos pantallas, todo encontrable |
| **F3 · Pantallas clave** | Hoy (tarjeta «Hoy»), Entrenar (botón principal + modo foco), Comidas (FAB y lista del día) | El uso diario a 1-2 toques |
| **F4 · Ordenador** | Rejillas y lista-detalle en Historial, Rutinas y Ejercicios | Se ve como una app de escritorio |
| **F5 · Acabado** | Estados vacío, carga y error; revisión de contraste y tamaños táctiles; tema claro | Sensación de producto terminado |

---

## 7. Decisiones (2026-11-12)
1. **Coach como pestaña.** ✅
2. **Color de marca:** se elige probando. La apariencia tiene dos ajustes independientes (modo: oscuro/claro/automático, y 9 colores de marca) en Configuración → Apariencia. Cuando lo tengas claro, se fija el color por defecto.
3. **Tema claro:** sí, además del oscuro (y «automático», que sigue al móvil). ✅
4. **Maquetas:** de momento no. Queda como opción para pantallas futuras o cambios grandes.

**Estado:** ✅ F1-F5 hechas (2026-11-12). Pendiente: revisión visual en el móvil y en el ordenador, y elegir el color de marca por defecto.

| Fase | Hecho |
|---|---|
| F1 | Tokens (`styles/tokens.css`): modo oscuro/claro/automático × 9 colores de marca. Menú adaptable y barra superior con avatar y flecha atrás (`components/BottomNav.tsx`, `styles/shell.css`). Modo foco en el entreno, zonas seguras y «N» de Next oculta. |
| F2 | Progreso en una pantalla con 4 segmentos. Entrenar con Rutinas, Ejercicios e Historial. Comidas con Día, Semana y Peso y objetivo. **Cuenta** unifica perfil, objetivos, conexiones, apariencia y seguridad. Las rutas antiguas redirigen. `components/ui/Segmented` y `lib/useTabParam` (`?tab=`). |
| F3 | Componentes base (`components/ui/`: Card, StatTile, Button, Fab, EmptyState, Skeleton). **Hoy** con tarjeta principal (entrenar, suave o descanso) y rejilla compacta. **Entrenar** con «Empezar: {día}». **Comidas** con botón flotante «Añadir». Títulos unificados y «Ver todos» en las listas largas. |
| F4 | Ordenador y tablet (`styles/layout.css`): Hoy en 2 columnas, Progreso en rejilla, **lista y detalle lado a lado** en Historial y Ejercicios (`?id=`), Comidas con resumen fijo a la izquierda, y las hojas pasan a diálogos centrados. |
| F5 | Esqueletos de carga, estados vacíos con acción, «Reintentar» en los errores, foco visible, menos movimiento si el sistema lo pide, tamaños táctiles y valores en StatTile. |

**Ajustes tras la primera prueba (2026-11-12):**
- Progreso queda en 3 segmentos: el peso pasa a Resumen.
- Entrenar: los botones parten el texto si un nombre de rutina es largo, y «Entreno libre» va separado de la tarjeta de la rutina.
- Tarjeta de rutina: «Editar» y «Analizar» visibles, el resto en el menú «⋯» (`components/ui/OverflowMenu`).
- Service worker v2: siempre busca primero la versión nueva. La v1 servía código viejo y provocaba el error en Apariencia.

**Pendiente menor:** «Cargando…» de texto en Importar, Registrar y dos hojas, y reintentar en la pestaña Fatiga. Pasar los formularios antiguos al componente Button.
