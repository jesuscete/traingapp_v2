"use client";

import { useEffect } from "react";

/**
 * Registra el service worker solo con HTTPS (Tailscale): ahí la app es instalable y
 * funciona sin conexión. En http://localhost o por IP de la LAN no se registra.
 */
export function ServiceWorker() {
  useEffect(() => {
    if (!("serviceWorker" in navigator) || window.location.protocol !== "https:") return;
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => undefined);
  }, []);
  return null;
}
