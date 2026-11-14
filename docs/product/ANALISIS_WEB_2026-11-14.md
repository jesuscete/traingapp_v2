# Análisis de la web · 14-11-2026

Foto del estado actual (rama `feature/rebranding1`, sobre `dev` 7c6a797): estructura, calidad del código, SOLID, hasta dónde puede llegar la app y qué le falta. Cifras medidas sobre el código, no estimadas.

---

## 1. Mapa del sistema

```
                         Móvil (PWA instalada) / navegador
                                       │ https://traingapp.tail965cc3.ts.net
                                       ▼
                              Tailscale serve (HTTPS)
                         "/" ─────────┘        └──────── "/api"
                          ▼                                  ▼
               ┌────────────────────┐   JSON + JWT  ┌──────────────────────┐  token interno  ┌──────────────┐
               │ web · Next 16      │ ────────────▶ │ api-gateway · FastAPI│ ──────────────▶ │ ai-parser    │──▶ claude CLI
               │ React 19 · TS      │               │ :8000                │                 │ :8100        │
               │ :3000 (todo cliente)│               │ router determinista  │◀── cola Redis ──│ + worker     │
               └────────────────────┘               └───┬──────────┬───────┘                 └──────────────┘
                 localStorage: sesión,                  │          │
                 entreno en curso, cola offline     PostgreSQL   Redis            Garmin (poller 30 min)
                 sw.js: caché offline               (datos)     (chat, propuestas, Open Food Facts
                                                                 rate limit)       diccionario propio de comidas
```

## 2. Mapa mental de la web (`services/web`)

```
web
├─ app/            26 rutas · 4 981 líneas · TODAS "use client"
│   ├─ Pestañas:   dashboard (Hoy) · entrenar · comidas · progreso · chat (Coach)
│   ├─ Cuenta:     cuenta/{perfil, objetivos, conexiones, apariencia, seguridad}
│   ├─ Detalle:    entrenos/[id] · ejercicios/[id] · rutinas · registrar · importar
│   ├─ Login:      / · registro
│   └─ Redirecciones antiguas (7 líneas c/u): perfil, fatiga, analisis, preparacion, objetivos, configuracion
├─ components/     113 ficheros · 14 128 líneas, agrupados por dominio
│   ├─ ui/         primitivas: Button, Card, Segmented, Skeleton, StatTile, Fab, EmptyState, OverflowMenu
│   ├─ shell:      BottomNav, AvatarMenu, ThemeProvider, ServiceWorker, PendingSync
│   └─ dominio:    workout · gym · rutinas · train · activity · metrics · nutrition · progress · home · account · sport…
├─ lib/            43 ficheros · 6 230 líneas
│   ├─ api.ts      cliente HTTP único (≈100 métodos) + refresco de token
│   ├─ types.ts    1 347 líneas: todos los tipos de la API escritos a mano
│   ├─ lógica pura: macros, bodyTrend, strength (copia del backend), wod, metrics, routineReview, todayDone
│   ├─ hooks:      useToken, useCatalog, useActiveWorkout, useChatEngine, useRestTimer, useWakeLock…
│   └─ workout/    entreno en curso local + cola offline (ops, storage, sync, payload)
└─ styles/         tokens.css (temas) · shell.css · ui.css · layout.css  +  app/globals.css (2 996 líneas)
```

Flujo típico de una pantalla:

```
page.tsx ──useToken()──▶ token ──props──▶ Componente ──useEffect──▶ api.getX(token) ──▶ useState ──▶ render
```

## 3. Cifras

| | Web | api-gateway | ai-parser |
|---|---|---|---|
| Código | ≈26 000 líneas TS/CSS | ≈22 000 líneas Python | ≈3 000 líneas |
| Tests | 5 ficheros (solo `lib/`) | 58 ficheros · 390 tests | 13 ficheros |
| Tipado | `strict: true`, 1 `any` | type hints + pydantic | ídem |
| Linter | **ninguno** | ruff + mypy | ruff |

Ficheros más grandes de la web: `globals.css` 2 996 · `types.ts` 1 347 · `api.ts` 790 · `RoutineEditor.tsx` 686 · `dashboard/page.tsx` 517.

---

## 4. Lo que está bien

- **Separación de responsabilidades en el sistema.** La web no calcula nada importante, el gateway es el único que toca la BD y la IA está aislada en un servicio sin estado. Cambiar de proveedor de IA (`APP_LLM_PROVIDER`) no toca ni la web ni la BD.
- **Backend por capas limpio:** `api/` (HTTP) → `services/` (casos de uso) → `analytics/` (cálculo puro, sin BD) → `crud/` (consultas) → `models/`. Los routers no hacen consultas SQL (solo `catalog.py` tiene 2). Esto es lo más sólido del proyecto.
- **IA como capa opcional (ADR-011):** el router determinista responde lo frecuente sin Claude; si la IA cae, la app sigue funcionando.
- **Organización de componentes por dominio** (`nutrition/`, `workout/`…), no por tipo. Escala bien.
- **Lógica de interfaz extraída a funciones puras y testeadas** (`macros.ts`, `bodyTrend.ts`, `todayDone.ts`, `workout/ops.ts`).
- **Tokens de diseño** con variables CSS: el cambio de tema de hoy tocó un fichero.
- **Offline real en el gimnasio:** entreno local + cola de reintento + service worker.
- **Seguridad razonable para uso personal:** JWT corto con refresh rotatorio, rate limit, sin puertos abiertos.

## 5. Problemas, por prioridad

### Alta
1. **Toda la web es "cliente" y cada pantalla pide sus datos al montarse.** 26/26 páginas `"use client"`, 132 `useEffect`, sin caché compartida. Consecuencias: esqueletos grises en cada navegación, peticiones repetidas al volver a una pantalla, y la sensación de "poco fluido" que notas (sumada a `next dev`). **Arreglo:** una capa de datos con caché (TanStack Query o SWR): al volver a Hoy se pinta al instante lo que había y se refresca por detrás. Es el cambio con más impacto percibido.
2. **Se sirve en modo desarrollo.** `next dev` compila cada ruta la primera vez y manda código sin optimizar. **Arreglo:** `next build && next start` para el uso diario (flag `-Prod` en `dev-up.ps1`).
3. **`globals.css` de 2 996 líneas, global.** Cualquier clase puede chocar con otra; ya conviven estilos de tres épocas (OpenCode, M9 F1, fixes). 43 `style={{}}` en línea y ~24 colores hex fuera de los tokens. **Arreglo:** CSS Modules por componente (`Button.module.css`) migrando poco a poco, empezando por lo que se toque.

### Media
4. **Tipos de la API duplicados a mano.** `types.ts` (1 347 líneas) replica los esquemas pydantic; si el backend cambia un campo, la web no se entera hasta que falla. **Arreglo:** generar los tipos desde `/openapi.json` (`openapi-typescript`) en un script.
5. **Lógica duplicada en dos lenguajes.** `lib/strength.ts` es "copia EXACTA" de `strength.py`. Mantener a mano dos copias acaba divergiendo. **Arreglo:** que el backend devuelva el 1RM calculado, o vectores de test compartidos en `shared/` comprobados en ambos lados.
6. **El token viaja por props.** Cada método de `api.ts` recibe `token` (≈200 apariciones) y cada componente lo pasa hacia abajo. **Arreglo:** que `api.ts` lea la sesión él mismo (ya lo hace al refrescar); los componentes dejan de saber qué es un token.
7. **Componentes y páginas demasiado grandes:** `RoutineEditor` (686), `dashboard/page` (517), `GoalsForm` (406) mezclan carga de datos, estado, reglas y vista.
8. **Código muerto:** ~20 métodos de `api.ts` sin uso (todo `/live/*`, `/chat/plan/*`, `stats/overview|volume|cardio|progress`…), y en el backend `app/chat/` (2 387 líneas, `plan_session.py` 1 179) y endpoints `/live` que la web nueva ya no usa. `shared/contracts` casi vacío.

### Baja
9. **Sin linter en la web** (ESLint + reglas de hooks detectarían dependencias de `useEffect` mal puestas).
10. **Sin tests de componentes ni end-to-end.** Un Playwright con 5 recorridos (login, entreno, comida, coach, importar) cubriría lo que rompe de verdad.
11. **Accesibilidad no auditada** (contraste de los temas nuevos, foco, lectores de pantalla).
12. **Ficheros de backend grandes:** `services/nutrition.py` 1 071, `api/stats.py` 688.

## 6. SOLID, aplicado a esta web

| Principio | Qué significa aquí | Estado | Ejemplo |
|---|---|---|---|
| **S** · Responsabilidad única | Cada pieza tiene un motivo para cambiar | 🟡 Bien en `lib/` y backend; mal en páginas grandes | `macros.ts` solo calcula macros ✅ · `dashboard/page.tsx` carga 6 fuentes de datos, decide avisos y pinta ❌ |
| **O** · Abierto/cerrado | Añadir sin modificar | ✅ Bueno | Un deporte nuevo = un JSON en `sport_profiles/`; un tema nuevo = un bloque en `tokens.css` |
| **L** · Sustitución | Implementaciones intercambiables | ✅ En ai-parser | `claude_cli` / `ollama` / `openai` / `stub` cumplen el mismo contrato |
| **I** · Interfaces pequeñas | No depender de lo que no usas | 🟡 | `api.ts` es un objeto con ≈100 métodos que todo importa; mejor `api/nutrition.ts`, `api/training.ts`… |
| **D** · Inversión de dependencias | Depender de abstracciones | 🟡 Backend sí (`Depends(get_db)`), web no | Los componentes llaman a `api.getX` directamente; con hooks (`useDay(date)`) se podría cambiar la fuente (caché, offline, mock) sin tocar la vista |

**En una frase:** el backend está cerca de "arquitectura limpia"; la web es "organizada pero acoplada": la estructura es buena, el reparto de responsabilidades dentro de las pantallas no.

## 7. A qué puede aspirar

| Nivel | Qué es | Qué falta para llegar |
|---|---|---|
| **Hoy** | App personal muy completa (entreno, comidas, fatiga, Garmin, coach) en tu PC vía Tailscale | — |
| **App personal pulida** | Instantánea, estable, que no se rompa al tocar | Modo producción, capa de caché, linter, Playwright básico, decidir tema |
| **App para unos pocos usuarios** (amigos, un club) | Varias cuentas reales sin tu PC encendido | VPS o nube, Docker para todo, email (recuperar contraseña), copias fuera del PC, monitorización de errores (Sentry), IA con API de pago por uso en vez de tu suscripción |
| **Producto público** | Competir con Hevy / Strong / MyFitnessPal | App nativa o Capacitor (HealthKit/Health Connect), pagos, RGPD formal, soporte, CI/CD, escalado |

Lo diferencial que ya tienes y esas apps no: **fatiga muscular por deporte + preparación para un deporte concreto (boxeo, triatlón) + coach que conoce tus datos**. Eso es lo que merece pulirse.

## 8. Qué le falta (lista corta y ordenada)

1. Modo producción para el uso diario (inmediato, una hora).
2. Capa de datos con caché en la web (fluidez).
3. Decidir tema y fuentes → retirar los no elegidos y el modo claro pendiente.
4. Borrar código muerto (web + `app/chat` + `/live`) tras confirmar que nada lo usa.
5. ESLint + generación de tipos desde OpenAPI.
6. Partir `globals.css` y las tres pantallas más grandes al tocarlas.
7. 5 tests end-to-end con Playwright.
8. Pensando en más usuarios: despliegue fuera del PC, email, Sentry.
