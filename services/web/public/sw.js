/*
 * Service worker de TrainingApp (M8): la app se abre aunque no haya cobertura en el gimnasio.
 * - Páginas: red primero; sin red, la última versión guardada (o la del entreno).
 * - Recursos estáticos de Next (/_next/static, iconos): también red primero. En modo desarrollo
 *   sus nombres no cambian entre versiones; servirlos de la caché dejaba código viejo (v1).
 * - API (/api, GET): red primero; sin red, la última respuesta guardada en ESTE móvil.
 *   Nunca se guardan /api/auth ni peticiones que no sean GET. Al cerrar sesión se borra todo.
 */
const VERSION = "v2"; // cambiar la versión borra las cachés anteriores
const PAGES = `pages-${VERSION}`;
const STATIC = `static-${VERSION}`;
const API = `api-${VERSION}`;
const PRECACHE = ["/dashboard", "/entrenar", "/comidas", "/manifest.webmanifest", "/icon-192.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(PAGES)
      .then((cache) => Promise.allSettled(PRECACHE.map((url) => cache.add(url))))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  const keep = new Set([PAGES, STATIC, API]);
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => !keep.has(k)).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("message", (event) => {
  if (event.data === "clear-cache") {
    event.waitUntil(caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k)))));
  }
});

async function networkFirst(request, cacheName, fallbackUrl) {
  const cache = await caches.open(cacheName);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch (err) {
    const cached = (await cache.match(request)) || (fallbackUrl && (await cache.match(fallbackUrl)));
    if (cached) return cached;
    throw err;
  }
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/auth")) return;
  if (url.pathname.startsWith("/_next/webpack-hmr") || url.pathname.includes("__nextjs")) return;

  if (url.pathname.startsWith("/api/")) {
    event.respondWith(networkFirst(request, API));
  } else if (request.mode === "navigate") {
    event.respondWith(networkFirst(request, PAGES, "/dashboard"));
  } else if (url.pathname.startsWith("/_next/static/") || /\.(png|svg|ico|webmanifest)$/.test(url.pathname)) {
    event.respondWith(networkFirst(request, STATIC));
  }
});
