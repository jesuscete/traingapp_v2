import type { NextConfig } from "next";

// En modo LAN (scripts/dev-up.ps1 -Lan) el móvil accede por IP: Next dev
// necesita permitir ese origen para servir HMR y recursos de desarrollo.
const lanOrigin = process.env.LAN_DEV_ORIGIN;

// Cabeceras de seguridad (M7). La CSP es deliberadamente ligera: Next usa scripts en
// línea y la app carga imágenes externas (ejercicios, mapas de OpenStreetMap).
const SECURITY_HEADERS = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  // La cámara se reserva para el escáner de códigos de barras (M8), solo en la propia app.
  { key: "Permissions-Policy", value: "camera=(self), microphone=(), geolocation=()" },
  {
    key: "Content-Security-Policy",
    value: "frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'",
  },
];

const nextConfig: NextConfig = {
  ...(lanOrigin ? { allowedDevOrigins: [lanOrigin] } : {}),
  poweredByHeader: false,
  async headers() {
    return [{ source: "/(.*)", headers: SECURITY_HEADERS }];
  },
};

export default nextConfig;
