"use client";

import { Smartphone } from "lucide-react";
import { useEffect, useState } from "react";

type InstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

function isStandalone(): boolean {
  return window.matchMedia("(display-mode: standalone)").matches;
}

/** Botón «Instalar la app» (Android/Chrome). Solo aparece con HTTPS y si aún no está instalada. */
export function InstallAppCard() {
  const [prompt, setPrompt] = useState<InstallPromptEvent | null>(null);
  const [installed, setInstalled] = useState(false);
  const [secure, setSecure] = useState(true);

  useEffect(() => {
    setInstalled(isStandalone());
    setSecure(window.location.protocol === "https:");
    const onPrompt = (event: Event) => {
      event.preventDefault();
      setPrompt(event as InstallPromptEvent);
    };
    const onInstalled = () => setInstalled(true);
    window.addEventListener("beforeinstallprompt", onPrompt);
    window.addEventListener("appinstalled", onInstalled);
    return () => {
      window.removeEventListener("beforeinstallprompt", onPrompt);
      window.removeEventListener("appinstalled", onInstalled);
    };
  }, []);

  if (installed) return null;

  return (
    <section className="energy-card">
      <h3 className="garmin-title">
        <Smartphone size={20} strokeWidth={1.75} aria-hidden /> App en el móvil
      </h3>
      {!secure ? (
        <p className="subtitle">
          Para instalarla, abre la app con la dirección de Tailscale (https://…ts.net).
        </p>
      ) : prompt ? (
        <>
          <p className="subtitle">
            Instálala para abrirla desde un icono, a pantalla completa y aunque no haya cobertura.
          </p>
          <button
            type="button"
            onClick={async () => {
              await prompt.prompt();
              const choice = await prompt.userChoice;
              if (choice.outcome === "accepted") setInstalled(true);
              setPrompt(null);
            }}
          >
            Instalar la app
          </button>
        </>
      ) : (
        <p className="subtitle">
          En Chrome: menú ⋮ → «Instalar aplicación» (o «Añadir a pantalla de inicio»).
        </p>
      )}
    </section>
  );
}
