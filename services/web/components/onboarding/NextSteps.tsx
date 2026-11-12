"use client";

import Link from "next/link";
import { useState } from "react";
import { Activity, HeartPulse, Target, Watch, type LucideIcon } from "lucide-react";

import { api } from "@/lib/api";
import type { Onboarding } from "@/lib/types";

const META: Record<string, { icon: LucideIcon; why: string }> = {
  garmin: { icon: Watch, why: "Tus entrenos, sueño y pulso en reposo llegarán solos" },
  goal: { icon: Target, why: "La app y el Coach se orientan a tu meta" },
  secondary_sports: { icon: Activity, why: "Para adaptar la fatiga y el análisis" },
  max_hr: { icon: HeartPulse, why: "Zonas de pulso precisas (si no la sabes, se estima)" },
};

type Props = {
  token: string;
  onboarding: Onboarding;
  skipped: string[];
  onChanged: () => void;
};

export function NextSteps({ token, onboarding, skipped, onChanged }: Props) {
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const total = onboarding.recommended.length;
  const done = onboarding.recommended.filter((s) => s.done).length;
  const pending = onboarding.recommended.filter((s) => !s.done && !s.skipped);
  if (!onboarding.complete || pending.length === 0) return null;

  async function skip(key: string) {
    setBusy(key);
    setError(null);
    try {
      await api.updateProfile(token, {
        onboardingSkipped: Array.from(new Set([...skipped, key])),
      });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo omitir");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="hm-card">
      <h3>Saca más partido a la app</h3>
      <p className="muted">
        {done} de {total} completados
      </p>
      {pending.map((s) => {
        const meta = META[s.key] ?? { icon: Target, why: "" };
        const Icon = meta.icon;
        return (
          <div key={s.key} className="hm-goal">
            <span className="hub-icon">
              <Icon size={18} strokeWidth={1.75} aria-hidden="true" />
            </span>
            <span className="hub-text">
              <span className="hub-label">{s.label}</span>
              <span className="hub-sub">{meta.why}</span>
            </span>
            {s.href && <Link href={s.href}>Ir</Link>}
            <button
              type="button"
              className="link"
              disabled={busy === s.key}
              onClick={() => skip(s.key)}
            >
              Omitir
            </button>
          </div>
        );
      })}
      {error && <p className="error">{error}</p>}
    </section>
  );
}
