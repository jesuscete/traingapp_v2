# ADR-008 · Sincronización con Garmin mediante la API personal oficial

**Fecha:** 2026-11-12 · **Estado:** aceptada · **Hito:** M6.2

## Problema
Las actividades y la salud diaria del reloj tenían que subirse a mano (M6.1). Strava quedó descartada (prohíbe el uso con IA). La API de empresa de Garmin exige ser una organización y tiene coste.

## Decisión
- **Fuente:** la **API personal de Garmin Connect** (abierta en octubre de 2026). Es gratuita, oficial y de solo lectura de los datos propios. El usuario crea una clave en `connect.garmin.com/app/settings/personalApiToken` y la pega en Configuración.
- **Autenticación:** la clave se canjea por un token JWT de 24 h (`Authorization: ApiKey …`). El token se reutiliza hasta 1 h antes de que caduque.
  - **Cifrado:** clave y token se guardan cifrados con Fernet (`APP_ENCRYPTION_KEY` o, si no se define, una clave derivada de `APP_JWT_SECRET`).
- **Actividades:** se listan por rango de fechas, se descarga el **archivo original (ZIP → FIT)** y pasa por el importador de M6.1, que calcula zonas, TRIMP, kcal, mapa y fatiga.
  - **Duplicados:** `external_source = "garmin"` y `external_id = "garmin:<id>"`. Lo ya subido a mano se detecta por huella o por solape y no se duplica.
- **Salud diaria** (últimos 28 días): FC en reposo, horas de sueño y VFC (anoche frente a la media semanal) van a `daily_readiness`, que modula la recuperación de la fatiga.
  - Nunca se sobrescriben las agujetas ni el día de descanso, que pone el usuario.
  - La FC en reposo rellena el perfil solo si estaba vacía.
- **Cuándo se sincroniza:**
  - La API personal no envía avisos (no hay *push*), así que se usa un sondeo cada `APP_GARMIN_POLL_MINUTES` (30 por defecto; 0 lo desactiva), que corre dentro del gateway.
  - Además, se sincroniza al abrir el inicio si hace más de 15 min de la última.
  - Y hay un botón «Sincronizar ahora».
- **Primera conexión:** trae 30 días (`APP_GARMIN_HISTORY_DAYS`). El botón «Traer últimos 90 días» permite ir más atrás si Garmin lo permite.
- **Lectura tolerante:** el cliente oficial no documenta los esquemas de respuesta, así que los datos se buscan por nombre de campo en cualquier nivel (`calendarDate`, `restingHeartRate`, `sleepTimeSeconds`, `lastNightAvg`/`weeklyAvg`).

## Consecuencias
- ✅ Las actividades aparecen solas, como mucho unos 30 min después de sincronizar el reloj con el móvil. Lo mismo para sueño y FC en reposo, que alimentan la fatiga.
- ✅ Se reutilizan el importador de M6.1 y su deduplicación; no hay un segundo camino de cálculo.
- ⚠️ La clave caduca (de 30 días a 1 año). Si Garmin la rechaza, la conexión queda en «error» y se pide una nueva.
- ⚠️ Los nombres de campo de salud se han deducido. Hay que validarlos con la cuenta real y ajustarlos si alguno viene vacío.
- ⚠️ Los términos de la API personal limitan su uso a los datos propios (nada de app comercial con terceros). Encaja con el uso actual, pero hay que revisarlo antes de abrir la app a más usuarios (M8).
- ⚠️ El sondeo vive en el proceso del gateway. Con varias réplicas habría que moverlo a un worker con bloqueo.
