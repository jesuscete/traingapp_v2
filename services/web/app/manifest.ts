import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: "/",
    name: "TrainingApp",
    short_name: "TrainingApp",
    description: "Registra y analiza tus entrenamientos",
    start_url: "/dashboard",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#15161a",
    theme_color: "#15161a",
    lang: "es",
    icons: [
      { src: "/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
    ],
    shortcuts: [
      { name: "Empezar entreno", url: "/entrenar", icons: [{ src: "/icon-192.png", sizes: "192x192" }] },
      { name: "Registrar comida", url: "/comidas", icons: [{ src: "/icon-192.png", sizes: "192x192" }] },
      { name: "Coach", url: "/chat", icons: [{ src: "/icon-192.png", sizes: "192x192" }] },
    ],
  };
}
