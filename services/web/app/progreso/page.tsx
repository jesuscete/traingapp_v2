"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { BottomNav } from "@/components/BottomNav";
import { WeekCard } from "@/components/home/WeekCard";
import { api } from "@/lib/api";
import { todayISO } from "@/lib/nutrition";
import type { HomeSummary } from "@/lib/types";
import { useToken } from "@/lib/useToken";

const TILES = [
  { href: "/entrenos", icon: "📅", label: "Historial" },
  { href: "/fatiga", icon: "🔥", label: "Fatiga muscular" },
  { href: "/preparacion", icon: "🥊", label: "Preparación de boxeo" },
  { href: "/analisis", icon: "📈", label: "Carga y análisis" },
  { href: "/comidas#peso", icon: "⚖️", label: "Peso" },
];

export default function Progreso() {
  const token = useToken();
  const [home, setHome] = useState<HomeSummary | null>(null);

  useEffect(() => {
    if (!token) return;
    api
      .getHome(token, new Date().getHours(), todayISO())
      .then(setHome)
      .catch(() => setHome(null));
  }, [token]);

  return (
    <main className="dashboard">
      <BottomNav />
      <section className="welcome">
        <h2>Progreso</h2>
      </section>
      {home && (
        <section className="hm-card">
          <h2>Cómo estás avanzando</h2>
          <WeekCard home={home} showDays={false} />
        </section>
      )}
      <div className="hub-grid">
        {TILES.map((t) => (
          <Link key={t.href} className="hub-tile" href={t.href}>
            <span className="hub-icon" aria-hidden="true">{t.icon}</span>
            <span className="hub-label">{t.label}</span>
          </Link>
        ))}
      </div>
    </main>
  );
}
