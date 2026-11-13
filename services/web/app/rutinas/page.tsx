"use client";

import { Suspense } from "react";

import { BottomNav } from "@/components/BottomNav";
import { ExercisesTab } from "@/components/train/ExercisesTab";
import { HistoryTab } from "@/components/train/HistoryTab";
import { RoutinesTab } from "@/components/train/RoutinesTab";
import { Segmented, type SegmentItem } from "@/components/ui/Segmented";
import { Skeleton } from "@/components/ui/Skeleton";
import { useTabParam } from "@/lib/useTabParam";

const TABS = ["rutinas", "ejercicios", "historial"] as const;
type Tab = (typeof TABS)[number];

const ITEMS: SegmentItem<Tab>[] = [
  { id: "rutinas", label: "Rutinas" },
  { id: "ejercicios", label: "Ejercicios" },
  { id: "historial", label: "Historial" },
];

function RutinaInner() {
  const [tab, setTab] = useTabParam<Tab>(TABS, "rutinas");
  return (
    <>
      <BottomNav />
      <div className="dashboard">
        <Segmented items={ITEMS} value={tab} onChange={setTab} label="Secciones de rutina" />
        {tab === "rutinas" && <RoutinesTab />}
        {tab === "ejercicios" && <ExercisesTab />}
        {tab === "historial" && <HistoryTab />}
      </div>
    </>
  );
}

export default function Rutina() {
  return (
    <Suspense fallback={<Skeleton height={160} />}>
      <RutinaInner />
    </Suspense>
  );
}
