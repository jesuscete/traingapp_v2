import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "Athlys",
    short_name: "Athlys",
    description: "Registra y analiza tus entrenamientos",
    start_url: "/dashboard",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#101820",
    theme_color: "#101820",
    lang: "es",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
    shortcuts: [
      { name: "Empezar entreno", url: "/entrenar", icons: [{ src: "/icon-192.png", sizes: "192x192" }] },
      { name: "Registrar comida", url: "/comidas", icons: [{ src: "/icon-192.png", sizes: "192x192" }] },
      { name: "Coach", url: "/chat", icons: [{ src: "/icon-192.png", sizes: "192x192" }] },
    ],
  };
}
