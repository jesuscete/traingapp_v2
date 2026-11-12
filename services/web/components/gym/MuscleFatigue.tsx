import { MuscleChart } from "@/components/MuscleChart";
import { MuscleFatigueMini } from "@/components/gym/MuscleFatigueMini";
import { aggregateByZone } from "@/lib/format";
import { translateZone } from "@/lib/labels";
import type { MuscleImpact } from "@/lib/types";

export function MuscleFatigue({ impacts }: { impacts: MuscleImpact[] }) {
  if (impacts.length === 0) return null;

  const sorted = [...impacts].sort((a, b) => b.activation - a.activation);
  const radarData = aggregateByZone(sorted, (item) => item.activation).map(
    (point) => ({ ...point, label: translateZone(point.label) }),
  );
  const bodyPoints = sorted.map((item) => ({
    muscleGroup: item.muscleGroup,
    value: Math.max(0, Math.min(1, item.activation)),
  }));

  return (
    <section className="block">
      <h2>Fatiga muscular estimada</h2>
      <div className="muscle-grid">
        <div className="muscle-radar">
          <MuscleChart
            size={360}
            showRadarLabels
            radarData={radarData}
            bodyPoints={bodyPoints}
          />
        </div>
        <MuscleFatigueMini impacts={sorted} />
      </div>
    </section>
  );
}
