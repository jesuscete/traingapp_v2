"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { BottomNav } from "@/components/BottomNav";
import { getTheme, setTheme, THEMES } from "@/lib/theme";

const TOKEN_KEY = "traingapp_token";

export default function Configuracion() {
  const router = useRouter();
  const [theme, setThemeId] = useState("");

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      router.replace("/");
      return;
    }
    setThemeId(getTheme());
  }, [router]);

  return (
    <main className="dashboard">
      <BottomNav />

      <section className="welcome">
        <h2>Configuración</h2>
        <p className="subtitle">Preferencias de la aplicación</p>
      </section>

      <section className="energy-card">
        <h3>Tema de color (beta)</h3>
        <p className="subtitle">
          Prueba distintas combinaciones de paleta. Se guarda en tu navegador.
        </p>
        <select
          value={theme}
          onChange={(e) => {
            setThemeId(e.target.value);
            setTheme(e.target.value);
          }}
        >
          <option value="">{THEMES[0].name}</option>
          {THEMES.slice(1).map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </section>
    </main>
  );
}
