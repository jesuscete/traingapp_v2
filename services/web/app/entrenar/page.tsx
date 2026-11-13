"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { BottomNav } from "@/components/BottomNav";
import { Skeleton } from "@/components/ui/Skeleton";
import { WorkoutScreen } from "@/components/workout/WorkoutScreen";
import { WorkoutStart } from "@/components/workout/WorkoutStart";
import { WorkoutSummary } from "@/components/workout/WorkoutSummary";
import { useActiveWorkout } from "@/lib/useActiveWorkout";
import { useToken } from "@/lib/useToken";
import type { WorkoutResult } from "@/lib/workout/types";

function EntrenarInner() {
  const router = useRouter();
  const token = useToken();
  const { workout, ready, update, start, clear } = useActiveWorkout(token);
  const legacyTab = useSearchParams().get("tab");
  const [result, setResult] = useState<WorkoutResult | null>(null);

  useEffect(() => {
    // Enlaces antiguos (/entrenar?tab=historial…): esas secciones viven ahora en Rutina.
    if (legacyTab) router.replace(`/rutinas?tab=${encodeURIComponent(legacyTab)}`);
  }, [legacyTab, router]);

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
          token={token}
          result={result}
          onClose={() => {
            setResult(null);
            router.push("/rutinas?tab=historial");
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
