"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { BottomNav } from "@/components/BottomNav";
import {
  ActivityForm,
  toLocalInput,
  type ActivitySubmit,
  type ActivityValues,
} from "@/components/metrics/ActivityForm";
import { api } from "@/lib/api";
import { translateDiscipline } from "@/lib/labels";
import { LOGGABLE_DISCIPLINES, combatTotals, emptyMetricsForm } from "@/lib/metrics";
import type { SessionIn } from "@/lib/types";
import { useToken } from "@/lib/useToken";

export default function Registrar() {
  const router = useRouter();
  const token = useToken();
  const [discipline, setDiscipline] = useState<string>("boxing");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initial = useMemo<ActivityValues>(
    () => ({
      performedAt: toLocalInput(new Date()),
      durationMinutes: "",
      intensity: null,
      note: "",
      metricsForm: emptyMetricsForm(),
    }),
    [],
  );

  async function submit(data: ActivitySubmit) {
    if (!token) return;
    setBusy(true);
    setError(null);
    let minutes = data.durationMinutes;
    if (minutes == null && data.metrics?.kind === "combat") {
      minutes = Math.max(1, Math.round(combatTotals(data.metrics.blocks).minutes));
    }
    const body: SessionIn = {
      discipline,
      rawText: `${translateDiscipline(discipline)}${minutes != null ? ` · ${minutes} min` : ""}`,
      performedAt: data.performedAtIso,
      ...(data.durationMinutes != null ? { durationMinutes: data.durationMinutes } : {}),
      ...(data.intensity != null ? { intensity: data.intensity } : {}),
      ...(data.note ? { note: data.note } : {}),
      ...(data.metrics ? { metrics: data.metrics } : {}),
      exercises: [],
    };
    try {
      const created = await api.createSession(token, body);
      router.push(`/entrenos/${created.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar la actividad");
      setBusy(false);
    }
  }

  return (
    <main className="dashboard">
      <BottomNav />
      <section className="welcome">
        <h2>Registrar actividad</h2>
        <p className="subtitle">
          ¿Gimnasio? <Link href="/entrenar">Ve a Entrenar</Link> · ¿Archivo del reloj?{" "}
          <Link href="/importar">Importar actividad</Link>
        </p>
      </section>

      {!token ? (
        <p className="muted">Cargando...</p>
      ) : (
        <>
          <section className="block m3-block">
            <label className="m3-field">
              <span>Disciplina</span>
              <select value={discipline} onChange={(e) => setDiscipline(e.target.value)}>
                {LOGGABLE_DISCIPLINES.map((d) => (
                  <option key={d} value={d}>
                    {translateDiscipline(d)}
                  </option>
                ))}
              </select>
            </label>
          </section>
          <ActivityForm
            discipline={discipline}
            initial={initial}
            submitLabel="Guardar actividad"
            busy={busy}
            error={error}
            onSubmit={(data) => void submit(data)}
          />
        </>
      )}
    </main>
  );
}
