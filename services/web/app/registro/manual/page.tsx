"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { BottomNav } from "@/components/BottomNav";

const TOKEN_KEY = "traingapp_token";

export default function RegistroManual() {
  const router = useRouter();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      router.replace("/");
      return;
    }
    setLoading(false);
  }, [router]);

  if (loading) {
    return (
      <main className="dashboard">
        <BottomNav />
        <p className="muted">Cargando...</p>
      </main>
    );
  }

  return (
    <main className="dashboard">
      <BottomNav />

      <section className="welcome">
        <h2>Registro manual</h2>
        <p className="subtitle">
          Añade ejercicios eligiéndolos del catálogo en lugar de escribirlos.
        </p>
      </section>

      <section className="block">
        <input type="search" placeholder="Buscar ejercicio..." disabled />

        <div className="progress-placeholder">
          <h3>Catálogo de ejercicios</h3>
          <p className="muted">
            En desarrollo. Aquí podrás buscar ejercicios de la base de datos y
            añadir series, peso y repeticiones manualmente, además del registro
            por chat.
          </p>
        </div>
      </section>
    </main>
  );
}
