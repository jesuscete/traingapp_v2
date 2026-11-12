"use client";

import { LoadSection } from "@/components/progress/LoadSection";
import { SportPrepSection } from "@/components/progress/SportPrepSection";

export function PerformanceTab() {
  return (
    <div className="tab-body">
      <SportPrepSection />
      <LoadSection />
    </div>
  );
}
