import { RadarChart } from "@/components/RadarChart";
import { MuscleFatigueMini } from "@/components/gym/MuscleFatigueMini";
import { translateMuscleGroup } from "@/lib/labels";
import type { MuscleImpact } from "@/lib/types";

export function MuscleFatigue({ impacts }: { impacts: MuscleImpact[] }) {
  if (impacts.length === 0) return null;

  const sorted = [...impacts].sort((a, b) => b.activation - a.activation);

  return (
    <section className="block">
      <h2>Fatiga muscular estimada</h2>
      <div className="muscle-grid">
        <div className="muscle-radar">
          <RadarChart
            size={360}
            showLabels
            data={sorted.map((item) => ({
              label: translateMuscleGroup(item.muscleGroup),
              value: item.activation,
            }))}
          />
        </div>
        <MuscleFatigueMini impacts={sorted} />
      </div>
    </section>
  );
}
