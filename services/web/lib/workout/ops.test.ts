import assert from "node:assert/strict";
import { test } from "node:test";

import { supersetRestHolder, toggleDone, toggleSupersetWithNext } from "@/lib/workout/ops";
import type { ActiveWorkout, WorkoutExercise } from "@/lib/workout/types";

function exercise(id: string, restSeconds = 90): WorkoutExercise {
  return {
    id,
    exerciseId: null,
    name: id,
    imageUrl: null,
    restSeconds,
    note: "",
    supersetGroupId: null,
    sets: [
      {
        id: `${id}-1`,
        type: "normal",
        weight: "20",
        reps: "10",
        rpe: "",
        done: false,
        targetRepsMin: null,
        targetRepsMax: null,
      },
    ],
    previous: [],
    records: null,
    history: "loaded",
  };
}

function workout(...ids: string[]): ActiveWorkout {
  return {
    version: 1,
    id: "w",
    title: "",
    startedAt: 0,
    routineDayId: null,
    exercises: ids.map((id) => exercise(id)),
    rest: null,
  };
}

const groups = (w: ActiveWorkout) => w.exercises.map((e) => e.supersetGroupId);

test("enlazar B+C y luego A+B deja los tres en la misma superserie", () => {
  let w = workout("A", "B", "C");
  w = toggleSupersetWithNext(w, "B");
  w = toggleSupersetWithNext(w, "A");
  const [a, b, c] = groups(w);
  assert.ok(a);
  assert.equal(a, b);
  assert.equal(b, c);
});

test("enlazar A+B y luego B+C también agrupa los tres", () => {
  let w = workout("A", "B", "C", "D");
  w = toggleSupersetWithNext(w, "A");
  w = toggleSupersetWithNext(w, "B");
  const [a, b, c, d] = groups(w);
  assert.ok(a && a === b && b === c);
  assert.equal(d, null);
});

test("separar en medio parte el grupo; un miembro suelto deja de ser superserie", () => {
  let w = workout("A", "B", "C");
  w = toggleSupersetWithNext(w, "A");
  w = toggleSupersetWithNext(w, "B");
  w = toggleSupersetWithNext(w, "A");
  const [a, b, c] = groups(w);
  assert.equal(a, null);
  assert.ok(b && b === c);
});

test("en superserie solo el último ejercicio del grupo dispara el descanso", () => {
  let w = workout("A", "B", "C");
  w = toggleSupersetWithNext(w, "A");
  w = toggleSupersetWithNext(w, "B");
  assert.equal(supersetRestHolder(w.exercises, w.exercises[0]), null);
  assert.equal(supersetRestHolder(w.exercises, w.exercises[2])?.id, "C");

  w = toggleDone(w, "A", "A-1");
  assert.equal(w.rest, null);
  w = toggleDone(w, "C", "C-1");
  assert.ok(w.rest);
});
