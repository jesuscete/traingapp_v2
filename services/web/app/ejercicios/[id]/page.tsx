"use client";

import { useParams } from "next/navigation";

import { BottomNav } from "@/components/BottomNav";
import { ExerciseDetail } from "@/components/train/ExerciseDetail";

export default function EjercicioDetalle() {
  const params = useParams<{ id: string }>();
  return (
    <main className="dashboard">
      <BottomNav />
      <ExerciseDetail id={params.id} />
    </main>
  );
}
