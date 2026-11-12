# ADR-009 · Blindaje (M7): sesiones rotatorias, límites, cabeceras, secretos y copias

**Fecha:** 2026-11-12 · **Estado:** aceptada · **Hito:** M7

## Problema
Para usar la app con datos reales y fuera de casa (vía Tailscale, M8) había varios riesgos:
- **Tokens:** de 30 días e imposibles de revocar.
- **Secretos:** el JWT secret y el token interno eran los de desarrollo, públicos en el repositorio. Cualquiera en la red podía falsificar sesiones o usar `/internal`.
- **Login:** no había límite de intentos.
- **Base de datos:** Postgres y Redis escuchaban en todas las interfaces.
- **Copias:** no había copias automáticas, ni forma de exportar o borrar la cuenta.
- **Dependencias:** había una vulnerabilidad crítica en Next.js 16.3.0.

## Decisión
- **Sesiones:**
  - **Tokens:** token de acceso JWT de 15 min con versión `tv`, más un **refresh token rotatorio**. El refresh es aleatorio de 48 bytes y se guarda solo su SHA-256 en `auth_sessions`.
  - **Reutilización:** si se reutiliza un refresh ya rotado, se revoca toda su familia (posible robo).
  - **Duración del refresh:** 30 días con «Recuérdame»; 12 h sin él (en ese caso se guarda en `sessionStorage`).
  - **Endpoints:** `/auth/refresh`, `/auth/logout` y `/auth/logout-all`. Este último incrementa `users.token_version` e invalida al momento los tokens de acceso vivos.
  - **Web:** `lib/session.ts` renueva el token una sola vez aunque haya varias peticiones a la vez. Siempre usa el token vigente y, ante un 401, renueva y reintenta.
- **Límite de intentos (Redis):**
  - Login: 5 fallos por email o 20 por IP en 15 min → 429 con `Retry-After`.
  - Registro: 10 por IP y hora.
- **Cabeceras:**
  - API: `nosniff`, `X-Frame-Options: DENY`, CSP `default-src 'none'`, `no-referrer`, `Cache-Control: no-store`, y HSTS si llega por HTTPS.
  - Web: `nosniff`, `DENY`, CSP ligera (sin iframes, `object-src 'none'`) y la cámara permitida solo en la propia app (escáner, M8).
- **Secretos:** `python -m app.cli init-secrets` genera `APP_JWT_SECRET`, `APP_INTERNAL_TOKEN` (en los dos `.env`) y `APP_ENCRYPTION_KEY`, y re-cifra las claves de Garmin guardadas. Los `.env` no se suben.
- **Red:** Postgres y Redis publicados solo en `127.0.0.1`. Al exterior solo llegan la web y la API (en M8, por Tailscale).
- **Cuenta (RGPD):**
  - `GET /profile/export` descarga todo en JSON: tablas con `user_id` y sus hijas, siguiendo las claves foráneas, sin hashes ni claves.
  - `POST /profile/delete` borra la cuenta y pide la contraseña.
- **Recuperar contraseña:** sin servidor de correo, desde el PC con `python -m app.cli reset-password <email>`, que además cierra todas las sesiones.
- **Copias:**
  - `scripts/backup-db.ps1` (pg_dump; guarda las últimas 14) y `scripts/restore-db.ps1`, que hace una copia previa y pide confirmación.
  - `scripts/register-backup-task.ps1` programa la copia diaria en el Programador de tareas.
- **Dependencias:** Next.js 16.4.6 (corrige la ejecución remota de código en `use cache`), sharp y source-map-js actualizados. `npm audit` da 0 vulnerabilidades.

## Consecuencias
- ✅ Una sesión robada caduca en 15 min o se corta al reutilizarla; «cerrar sesión en todos los dispositivos» funciona al momento.
- ✅ La base de datos no es accesible desde la red y los secretos ya no son públicos.
- ⚠️ El refresh vive en el almacenamiento del navegador, no en una cookie httpOnly. La API y la web están en orígenes distintos y por HTTP en la LAN. Se revisará con HTTPS (Tailscale) en M8.
- ⚠️ La verificación de email y el reseteo por correo quedan pendientes hasta que haya más usuarios (necesitan SMTP).
- ⚠️ La auditoría de dependencias de Python (pip-audit) no está automatizada; queda para la CI.
