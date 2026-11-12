"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { CalendarDays, ChartLine, ChevronRight, Flame, Scale, Target } from "lucide-react";

import { BottomNav } from "@/components/BottomNav";
import { WeekCard } from "@/components/home/WeekCard";
import { api } from "@/lib/api";
import { todayISO } from "@/lib/nutrition";
import type { HomeSummary } from "@/lib/types";
import { useToken } from "@/lib/useToken";

const TILES = [
  { href: "/entrenos", Icon: CalendarDays, label: "Historial", desc: "Todos tus entrenos" },
  { href: "/fatiga", Icon: Flame, label: "Fatiga muscular", desc: "Qué músculos están cargados" },
  { href: "/preparacion", Icon: Target, label: "Preparación", desc: "Qué te falta para tu deporte" },
  { href: "/analisis", Icon: ChartLine, label: "Carga y análisis", desc: "Volumen, intensidad y tendencias" },
  { href: "/comidas#peso", Icon: Scale, label: "Peso", desc: "Evolución de tu peso corporal" },
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
      <div className="hub-grid hub-list">
        {TILES.map((t) => (
          <Link key={t.href} className="hub-tile" href={t.href}>
            <span className="hub-icon"><t.Icon size={22} strokeWidth={1.75} aria-hidden="true" /></span>
            <span className="hub-text">
              <span className="hub-label">
                {t.label === "Preparación" && home?.sportLabel ? `Preparación: ${home.sportLabel}` : t.label}
              </span>
              <span className="hub-sub">{t.desc}</span>
            </span>
            <ChevronRight className="hub-chev" size={18} strokeWidth={1.75} aria-hidden="true" />
          </Link>
        ))}
      </div>
    </main>
  );
}
