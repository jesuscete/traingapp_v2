"use client";

import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { EquipmentCode, EquipmentPreset, UserEquipment } from "@/lib/types";

const TOKEN_KEY = "traingapp_token";
const USER_KEY = "traingapp_user";

const PRESETS: { key: EquipmentPreset; label: string; hint: string }[] = [
  { key: "gimnasio", label: "Gimnasio completo", hint: "Barras, máquinas, poleas…" },
  { key: "casa", label: "En casa", hint: "Mancuernas, kettlebell, bandas" },
  { key: "sin_material", label: "Sin material", hint: "Solo peso corporal" },
];

export const EQUIPMENT_LABELS: Record<EquipmentCode, string> = {
  barbell: "Barra",
  "e-z curl bar": "Barra Z",
  dumbbell: "Mancuernas",
  kettlebells: "Kettlebell",
  cable: "Polea",
  machine: "Máquinas",
  bands: "Bandas elásticas",
  "medicine ball": "Balón medicinal",
  "exercise ball": "Fitball",
  "foam roll": "Rodillo",
  "body only": "Peso corporal",
  other: "Otro (discos, cajón, comba…)",
};

const PRESET_EQUIPMENT: Record<EquipmentPreset, EquipmentCode[] | null> = {
  gimnasio: null,
  casa: ["dumbbell", "kettlebells", "bands", "exercise ball", "foam roll", "body only"],
  sin_material: ["body only"],
};

const ALL = Object.keys(EQUIPMENT_LABELS) as EquipmentCode[];

function available(eq: UserEquipment): Set<EquipmentCode> {
  const base = PRESET_EQUIPMENT[eq.preset];
  const set = new Set<EquipmentCode>(base ?? ALL);
  eq.extra.forEach((c) => set.add(c));
  eq.missing.forEach((c) => set.delete(c));
  return set;
}

/** «Con qué material entrenas»: filtra ejercicios, alternativas y planes (sin IA). */
export function EquipmentCard() {
  const [token, setToken] = useState<string | null>(null);
  const [equipment, setEquipment] = useState<UserEquipment>({
    preset: "gimnasio",
    extra: [],
    missing: [],
  });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let stored: string | null = null;
    try {
      stored = localStorage.getItem(TOKEN_KEY);
    } catch {
      stored = null;
    }
    if (!stored) return;
    setToken(stored);
    api
      .getProfile(stored)
      .then((p) => {
        if (p.equipment) setEquipment(p.equipment);
      })
      .catch(() => setError("No se pudo cargar tu material"));
  }, []);

  async function save(next: UserEquipment) {
    setEquipment(next);
    if (!token) return;
    setSaving(true);
    setMessage(null);
    setError(null);
    try {
      const updated = await api.updateProfile(token, { equipment: next });
      try {
        localStorage.setItem(USER_KEY, JSON.stringify(updated));
      } catch {
        /* sin almacenamiento local: no pasa nada */
      }
      setMessage("Guardado");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar");
    } finally {
      setSaving(false);
    }
  }

  function toggle(code: EquipmentCode) {
    const inPreset = (PRESET_EQUIPMENT[equipment.preset] ?? ALL).includes(code);
    const has = available(equipment).has(code);
    const extra = equipment.extra.filter((c) => c !== code);
    const missing = equipment.missing.filter((c) => c !== code);
    if (has) {
      if (inPreset) missing.push(code);
    } else if (!inPreset) {
      extra.push(code);
    }
    void save({ ...equipment, extra, missing });
  }

  const have = available(equipment);

  return (
    <section className="ob-section">
      <h2>Tu material</h2>
      <p className="muted">
        La app solo te propondrá ejercicios que puedas hacer, y te dará alternativas si te falta algo.
      </p>
      <div className="chips">
        {PRESETS.map((p) => (
          <button
            key={p.key}
            type="button"
            className={`chip chip-toggle${equipment.preset === p.key ? " on" : ""}`}
            disabled={saving}
            title={p.hint}
            onClick={() => void save({ preset: p.key, extra: [], missing: [] })}
          >
            {p.label}
          </button>
        ))}
      </div>
      <p className="muted m10-equipment-hint">Toca para marcar lo que tienes o te falta:</p>
      <div className="chips">
        {ALL.map((code) => (
          <button
            key={code}
            type="button"
            className={`chip chip-toggle${have.has(code) ? " on" : ""}`}
            disabled={saving}
            aria-pressed={have.has(code)}
            onClick={() => toggle(code)}
          >
            {EQUIPMENT_LABELS[code]}
          </button>
        ))}
      </div>
      {message && <p className="ok">{message}</p>}
      {error && <p className="error">{error}</p>}
    </section>
  );
}
