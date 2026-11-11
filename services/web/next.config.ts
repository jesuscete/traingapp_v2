import type { NextConfig } from "next";

// En modo LAN (scripts/dev-up.ps1 -Lan) el móvil accede por IP: Next dev
// necesita permitir ese origen para servir HMR y recursos de desarrollo.
const lanOrigin = process.env.LAN_DEV_ORIGIN;

const nextConfig: NextConfig = {
  ...(lanOrigin ? { allowedDevOrigins: [lanOrigin] } : {}),
};

export default nextConfig;
