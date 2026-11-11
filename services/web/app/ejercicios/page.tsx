"use client";

import { BottomNav } from "@/components/BottomNav";
import { ExerciseLibrary } from "@/components/gym/ExerciseLibrary";
import { useToken } from "@/lib/useToken";

export default function Ejercicios() {
  const token = useToken();
  return (
    <main className="dashboard">
      <BottomNav />
      <section className="welcome">
        <h2>Ejercicios</h2>
        <p className="subtitle">Biblioteca, favoritos y tu historial por ejercicio.</p>
      </section>
      <ExerciseLibrary token={token} />
    </main>
  );
}
