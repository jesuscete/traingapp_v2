"use client";

import { Skeleton } from "@/components/ui/Skeleton";
import { Suspense } from "react";

import { BottomNav } from "@/components/BottomNav";
import { FatigueTab } from "@/components/progress/FatigueTab";
import { PerformanceTab } from "@/components/progress/PerformanceTab";
import { SummaryTab } from "@/components/progress/SummaryTab";
import { Segmented, type SegmentItem } from "@/components/ui/Segmented";
import { useTabParam } from "@/lib/useTabParam";
import { useToken } from "@/lib/useToken";

// «Cuerpo» (peso) vive dentro de Resumen: menos pantallas. ?tab=cuerpo cae en Resumen.
const TABS = ["resumen", "fatiga", "rendimiento"] as const;
type Tab = (typeof TABS)[number];

const ITEMS: SegmentItem<Tab>[] = [
  { id: "resumen", label: "Resumen" },
  { id: "fatiga", label: "Fatiga" },
  { id: "rendimiento", label: "Rendimiento" },
];

function ProgresoInner() {
  const token = useToken();
  const [tab, setTab] = useTabParam<Tab>(TABS, "resumen");

  return (
    <main className="dashboard">
      <BottomNav />
      <Segmented items={ITEMS} value={tab} onChange={setTab} label="Secciones de progreso" />
      <div className="progress-wrap">
        {tab === "resumen" && token && <SummaryTab token={token} />}
        {tab === "fatiga" && <FatigueTab />}
        {tab === "rendimiento" && <PerformanceTab />}
      </div>
    </main>
  );
}

export default function Progreso() {
  return (
    <Suspense fallback={<Skeleton height={160} />}>
      <ProgresoInner />
    </Suspense>
  );
}
