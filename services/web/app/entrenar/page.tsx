"use client";

import { useRouter } from "next/navigation";
import { Suspense, useState } from "react";
import { FilePenLine, Watch } from "lucide-react";

import { BottomNav } from "@/components/BottomNav";
import { ExercisesTab } from "@/components/train/ExercisesTab";
import { HistoryTab } from "@/components/train/HistoryTab";
import { RoutinesTab } from "@/components/train/RoutinesTab";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { Segmented, type SegmentItem } from "@/components/ui/Segmented";
import { WorkoutScreen } from "@/components/workout/WorkoutScreen";
import { WorkoutStart } from "@/components/workout/WorkoutStart";
import { WorkoutSummary } from "@/components/workout/WorkoutSummary";
import { useTabParam } from "@/lib/useTabParam";
import { useActiveWorkout } from "@/lib/useActiveWorkout";
import { useToken } from "@/lib/useToken";
import type { WorkoutResult } from "@/lib/workout/types";

const TABS = ["rutinas", "ejercicios", "historial"] as const;
type Tab = (typeof TABS)[number];

const ITEMS: SegmentItem<Tab>[] = [
  { id: "rutinas", label: "Rutinas" },
  { id: "ejercicios", label: "Ejercicios" },
  { id: "historial", label: "Historial" },
];

function EntrenarInner() {
  const router = useRouter();
  const token = useToken();
  const { workout, ready, update, start, clear } = useActiveWorkout(token);
  const [tab, setTab] = useTabParam<Tab>(TABS, "rutinas");
  const [result, setResult] = useState<WorkoutResult | null>(null);

  if (!token || !ready) {
    return (
      <main className="dashboard">
        <BottomNav />
        <Skeleton height={190} />
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
            router.push("/entrenar?tab=historial");
          }}
        />
      </>
    );
  }

  if (workout) {
    return (
      <>
        <BottomNav hidden />
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
        <div className="actions-row">
          <Button variant="secondary" href="/registrar" icon={<FilePenLine size={20} strokeWidth={1.75} aria-hidden="true" />}>
            Registrar otra actividad
          </Button>
          <Button variant="secondary" href="/importar" icon={<Watch size={20} strokeWidth={1.75} aria-hidden="true" />}>
            Importar archivo
          </Button>
        </div>
        <Segmented items={ITEMS} value={tab} onChange={setTab} label="Secciones de entrenar" />
        {tab === "rutinas" && <RoutinesTab />}
        {tab === "ejercicios" && <ExercisesTab />}
        {tab === "historial" && <HistoryTab />}
      </div>
    </>
  );
}

export default function Entrenar() {
  return (
    <Suspense fallback={<Skeleton height={160} />}>
      <EntrenarInner />
    </Suspense>
  );
}
