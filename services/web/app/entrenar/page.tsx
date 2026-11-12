"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { BottomNav } from "@/components/BottomNav";
import { WorkoutScreen } from "@/components/workout/WorkoutScreen";
import { WorkoutStart } from "@/components/workout/WorkoutStart";
import { WorkoutSummary } from "@/components/workout/WorkoutSummary";
import { useActiveWorkout } from "@/lib/useActiveWorkout";
import { useToken } from "@/lib/useToken";
import type { WorkoutResult } from "@/lib/workout/types";

const HUB = [
  { href: "/registrar", icon: "📝", label: "Registrar actividad" },
  { href: "/importar", icon: "⌚", label: "Importar del reloj" },
  { href: "/rutinas", icon: "📋", label: "Rutinas" },
  { href: "/ejercicios", icon: "🏋️", label: "Ejercicios" },
];

export default function Entrenar() {
  const router = useRouter();
  const token = useToken();
  const { workout, ready, update, start, clear } = useActiveWorkout(token);
  const [result, setResult] = useState<WorkoutResult | null>(null);

  if (!token || !ready) {
    return (
      <main className="dashboard">
        <BottomNav />
        <p className="muted">Cargando...</p>
      </main>
    );
  }

  if (result) {
    return (
      <>
        <BottomNav />
        <WorkoutSummary
          result={result}
          onClose={() => {
            setResult(null);
            router.push("/entrenos");
          }}
        />
      </>
    );
  }

  if (workout) {
    return (
      <>
        <BottomNav />
        <WorkoutScreen
          token={token}
          workout={workout}
          update={update}
          onFinished={(r) => {
            clear();
            setResult(r);
          }}
          onDiscard={() => {
            if (window.confirm("¿Descartar el entreno? Se perderán todas las series.")) clear();
          }}
        />
      </>
    );
  }

  return (
    <>
      <BottomNav />
      <WorkoutStart token={token} onStart={start} />
      <div className="dashboard hub-wrap">
        <div className="hub-grid">
          {HUB.map((t) => (
            <Link key={t.href} className="hub-tile" href={t.href}>
              <span className="hub-icon" aria-hidden="true">{t.icon}</span>
              <span className="hub-label">{t.label}</span>
            </Link>
          ))}
        </div>
      </div>
    </>
  );
}
