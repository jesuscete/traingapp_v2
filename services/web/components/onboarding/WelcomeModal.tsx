"use client";

import { useState } from "react";

import { Sheet } from "@/components/nutrition/Sheet";
import { api } from "@/lib/api";
import { MAIN_SPORTS, OTHER_SPORTS } from "@/lib/sports";
import type { Onboarding, User } from "@/lib/types";

type Props = {
  token: string;
  user: User | null;
  onboarding: Onboarding;
  onSaved: () => void;
  onDismiss: () => void;
};

export function WelcomeModal({ token, user, onboarding, onSaved, onDismiss }: Props) {
  const missing = new Set(onboarding.required.filter((s) => !s.done).map((s) => s.key));
  const [sex, setSex] = useState(user?.sex ?? "");
  const [birthDate, setBirthDate] = useState(user?.birthDate ?? "");
  const [height, setHeight] = useState(user?.heightCm != null ? String(user.heightCm) : "");
  const [weight, setWeight] = useState(user?.weightKg != null ? String(user.weightKg) : "");
  const [primary, setPrimary] = useState(user?.primarySport ?? "");
  const [others, setOthers] = useState<string[]>(
    (user?.sports ?? []).filter((s) => s !== user?.primarySport),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleOther(key: string) {
    setOthers((prev) => (prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]));
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const body: Partial<User> = {};
    if (missing.has("sex")) {
      if (!sex) return setError("Elige tu sexo");
      body.sex = sex;
    }
    if (missing.has("birth_date")) {
      if (!birthDate) return setError("Indica tu fecha de nacimiento");
      body.birthDate = birthDate;
    }
    if (missing.has("height")) {
      const h = Number(height.replace(",", "."));
      if (!(h >= 80 && h <= 250)) return setError("La altura debe estar entre 80 y 250 cm");
      body.heightCm = h;
    }
    if (missing.has("weight")) {
      const w = Number(weight.replace(",", "."));
      if (!(w >= 20 && w <= 400)) return setError("El peso debe estar entre 20 y 400 kg");
      body.weightKg = w;
    }
    if (missing.has("primary_sport") || others.length > 0) {
      if (!primary) return setError("Elige tu deporte principal");
      body.primarySport = primary;
      body.sports = Array.from(new Set([primary, ...others]));
    }
    setSaving(true);
    setError(null);
    try {
      await api.updateProfile(token, body);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Sheet
      title={`Bienvenido/a${user?.name ? `, ${user.name}` : ""}`}
      onClose={onDismiss}
      footer={
        <>
          {error && <p className="error">{error}</p>}
          <button type="submit" form="welcome-form" disabled={saving}>
            {saving ? "Guardando..." : "Guardar y empezar"}
          </button>
          <button type="button" className="link" onClick={onDismiss}>
            Ahora no
          </button>
        </>
      }
    >
      <form id="welcome-form" onSubmit={submit}>
        <p className="muted">
          Con estos datos calculo tus calorías, tus zonas de pulso y tu preparación.
        </p>
        {missing.has("sex") && (
          <div>
            <p>Sexo</p>
            <div className="chips">
              {[
                ["male", "Hombre"],
                ["female", "Mujer"],
              ].map(([k, l]) => (
                <button
                  key={k}
                  type="button"
                  className={`chip chip-toggle${sex === k ? " on" : ""}`}
                  onClick={() => setSex(k)}
                >
                  {l}
                </button>
              ))}
            </div>
          </div>
        )}
        {missing.has("birth_date") && (
          <label>
            Fecha de nacimiento
            <input
              type="date"
              value={birthDate}
              max={new Date().toISOString().slice(0, 10)}
              onChange={(e) => setBirthDate(e.target.value)}
            />
          </label>
        )}
        {missing.has("height") && (
          <label>
            Altura (cm)
            <input
              type="number"
              inputMode="decimal"
              min="80"
              max="250"
              value={height}
              onChange={(e) => setHeight(e.target.value)}
            />
          </label>
        )}
        {missing.has("weight") && (
          <label>
            Peso (kg)
            <input
              type="number"
              inputMode="decimal"
              step="0.1"
              min="20"
              max="400"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
            />
          </label>
        )}
        {missing.has("primary_sport") && (
          <div>
            <p>Deporte principal</p>
            <div className="chips">
              {MAIN_SPORTS.map((s) => (
                <button
                  key={s.key}
                  type="button"
                  className={`chip chip-toggle${primary === s.key ? " on" : ""}`}
                  onClick={() => {
                    setPrimary(s.key);
                    setOthers((prev) => prev.filter((k) => k !== s.key));
                  }}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        )}
        <div>
          <p>Otros deportes (opcional)</p>
          <div className="chips">
            {OTHER_SPORTS.filter((s) => s.key !== primary).map((s) => (
              <button
                key={s.key}
                type="button"
                className={`chip chip-toggle${others.includes(s.key) ? " on" : ""}`}
                onClick={() => toggleOther(s.key)}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </form>
    </Sheet>
  );
}
