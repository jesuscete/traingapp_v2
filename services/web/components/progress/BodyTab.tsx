"use client";

import { WeightCard } from "@/components/nutrition/WeightCard";
import { todayISO } from "@/lib/nutrition";

export function BodyTab({ token }: { token: string }) {
  return (
    <div id="peso">
      <WeightCard token={token} day={todayISO()} onChanged={() => undefined} />
    </div>
  );
}
