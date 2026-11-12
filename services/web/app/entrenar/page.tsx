"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ChevronRight, ClipboardList, Dumbbell, FilePenLine, Watch } from "lucide-react";

import { BottomNav } from "@/components/BottomNav";
import { WorkoutScreen } from "@/components/workout/WorkoutScreen";
import { WorkoutStart } from "@/components/workout/WorkoutStart";
import { WorkoutSummary } from "@/components/workout/WorkoutSummary";
import { useActiveWorkout } from "@/lib/useActiveWorkout";
import { useToken } from "@/lib/useToken";
import type { WorkoutResult } from "@/lib/workout/types";

const HUB = [
  { href: "/registrar", Icon: FilePenLine, label: "Registrar actividad", desc: "Anota un entreno ya hecho" },
  { href: "/importar", Icon: Watch, label: "Importar del reloj", desc: "Archivos FIT, GPX o TCX" },
  { href: "/rutinas", Icon: ClipboardList, label: "Rutinas", desc: "Crea, evalúa y activa rutinas" },
  { href: "/ejercicios", Icon: Dumbbell, label: "Ejercicios", desc: "Biblioteca y favoritos" },
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
        <div className="hub-grid hub-list">
          {HUB.map((t) => (
            <Link key={t.href} className="hub-tile" href={t.href}>
              <span className="hub-icon"><t.Icon size={22} strokeWidth={1.75} aria-hidden="true" /></span>
              <span className="hub-text">
                <span className="hub-label">{t.label}</span>
                <span className="hub-sub">{t.desc}</span>
              </span>
              <ChevronRight className="hub-chev" size={18} strokeWidth={1.75} aria-hidden="true" />
            </Link>
          ))}
        </div>
      </div>
    </>
  );
}
