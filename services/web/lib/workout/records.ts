import { estimated1rm } from "@/lib/strength";
import { parseNum } from "@/lib/workout/ops";
import type { ActiveWorkout, PersonalRecord } from "@/lib/workout/types";


/** PR = supera el récord previo; sin historial previo no se marca. */
export function detectPersonalRecords(w: ActiveWorkout): PersonalRecord[] {
  const out: PersonalRecord[] = [];
  for (const ex of w.exercises) {
    const rec = ex.records;
    if (!rec) continue;
    let maxWeight = 0;
    let best1rm = 0;
    for (const s of ex.sets) {
      if (!s.done || s.type === "calentamiento") continue;
      const weight = parseNum(s.weight);
      const reps = parseNum(s.reps);
      if (weight == null || weight <= 0 || reps == null || reps <= 0) continue;
      maxWeight = Math.max(maxWeight, weight);
      const rpe = parseNum(s.rpe);
      best1rm = Math.max(best1rm, estimated1rm(weight, Math.round(reps), rpe) ?? 0);
    }
    if (rec.maxWeightKg != null && maxWeight > rec.maxWeightKg) {
      out.push({ exerciseName: ex.name, kind: "peso", value: maxWeight });
    }
    if (rec.bestE1rmKg != null && best1rm > rec.bestE1rmKg + 0.05) {
      out.push({ exerciseName: ex.name, kind: "1rm", value: Math.round(best1rm * 10) / 10 });
    }
  }
  return out;
}
