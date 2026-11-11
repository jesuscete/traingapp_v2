import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "TrainingApp",
    short_name: "TrainingApp",
    description: "Registra y analiza tus entrenamientos",
    start_url: "/dashboard",
    display: "standalone",
    background_color: "#15161a",
    theme_color: "#15161a",
    lang: "es",
    icons: [
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
      { src: "/icon.svg", sizes: "any", type: "image/svg+xml", purpose: "maskable" },
    ],
  };
}
