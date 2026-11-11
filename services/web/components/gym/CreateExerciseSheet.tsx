"use client";

import { useEffect, useState } from "react";

import { ApiError, api } from "@/lib/api";
import { translateMuscleGroup } from "@/lib/labels";
import type { CatalogExercise, MuscleGroupKey } from "@/lib/types";

const MUSCLE_KEYS: MuscleGroupKey[] = [
  "chest",
  "back",
  "shoulders",
  "biceps",
  "triceps",
  "forearms",
  "core",
  "quadriceps",
  "hamstrings",
  "glutes",
  "calves",
  "neck",
];

const EQUIPMENT_OPTIONS = [
  "barra",
  "mancuernas",
  "máquina",
  "polea",
  "peso corporal",
  "kettlebell",
  "banda",
  "otro",
];

const MAX_PRIMARY = 4;
const MAX_SECONDARY = 6;
const MAX_STEPS = 20;

type Props = {
  token: string;
  initialName?: string;
  onClose: () => void;
  onCreated: (exercise: CatalogExercise) => void;
};

export function CreateExerciseSheet({ token, initialName = "", onClose, onCreated }: Props) {
  const [name, setName] = useState(initialName);
  const [primary, setPrimary] = useState<MuscleGroupKey[]>([]);
  const [secondary, setSecondary] = useState<MuscleGroupKey[]>([]);
  const [equipment, setEquipment] = useState("");
  const [usesBodyweight, setUsesBodyweight] = useState(false);
  const [unilateral, setUnilateral] = useState(false);
  const [instructions, setInstructions] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  function togglePrimary(m: MuscleGroupKey) {
    setPrimary((list) => {
      if (list.includes(m)) return list.filter((x) => x !== m);
      return list.length >= MAX_PRIMARY ? list : [...list, m];
    });
    setSecondary((list) => list.filter((x) => x !== m));
  }

  function toggleSecondary(m: MuscleGroupKey) {
    setSecondary((list) => {
      if (list.includes(m)) return list.filter((x) => x !== m);
      return list.length >= MAX_SECONDARY ? list : [...list, m];
    });
  }

  async function submit() {
    const trimmed = name.trim();
    const steps = instructions
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    if (trimmed.length < 2 || trimmed.length > 120) {
      setError("El nombre debe tener entre 2 y 120 caracteres.");
      return;
    }
    if (primary.length === 0) {
      setError("Elige al menos un músculo principal.");
      return;
    }
    if (steps.length > MAX_STEPS) {
      setError(`Máximo ${MAX_STEPS} pasos de instrucciones.`);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const created = await api.createCustomExercise(token, {
        name: trimmed,
        primaryMuscles: primary,
        secondaryMuscles: secondary,
        equipment: equipment || null,
        usesBodyweight,
        unilateral,
        instructions: steps,
      });
      onCreated(created);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("Ya existe un ejercicio con ese nombre");
      } else {
        setError(err instanceof Error ? err.message : "No se pudo crear el ejercicio");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="sheet-backdrop ce-backdrop" role="presentation" onClick={onClose}>
      <div
        className="sheet ce-sheet"
        role="dialog"
        aria-modal="true"
        aria-label="Crear ejercicio"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sheet-head">
          <h3>Crear ejercicio</h3>
          <button type="button" className="sheet-close" onClick={onClose} aria-label="Cerrar">
            ✕
          </button>
        </div>
        <div className="sheet-body ce-body">
          <label className="ce-field">
            <span className="muted">Nombre</span>
            <input
              type="text"
              maxLength={120}
              value={name}
              placeholder="Ej: Press inclinado en máquina"
              autoComplete="off"
              onChange={(e) => setName(e.target.value)}
            />
          </label>

          <div className="ce-field">
            <span className="muted">
              Músculos principales ({primary.length}/{MAX_PRIMARY}) *
            </span>
            <div className="ce-chips" role="group" aria-label="Músculos principales">
              {MUSCLE_KEYS.map((m) => (
                <button
                  key={m}
                  type="button"
                  className={`ex-chip${primary.includes(m) ? " on" : ""}`}
                  aria-pressed={primary.includes(m)}
                  disabled={!primary.includes(m) && primary.length >= MAX_PRIMARY}
                  onClick={() => togglePrimary(m)}
                >
                  {translateMuscleGroup(m)}
                </button>
              ))}
            </div>
          </div>

          <div className="ce-field">
            <span className="muted">
              Músculos secundarios ({secondary.length}/{MAX_SECONDARY})
            </span>
            <div className="ce-chips" role="group" aria-label="Músculos secundarios">
              {MUSCLE_KEYS.filter((m) => !primary.includes(m)).map((m) => (
                <button
                  key={m}
                  type="button"
                  className={`ex-chip${secondary.includes(m) ? " on" : ""}`}
                  aria-pressed={secondary.includes(m)}
                  disabled={!secondary.includes(m) && secondary.length >= MAX_SECONDARY}
                  onClick={() => toggleSecondary(m)}
                >
                  {translateMuscleGroup(m)}
                </button>
              ))}
            </div>
          </div>

          <label className="ce-field">
            <span className="muted">Equipo</span>
            <select value={equipment} onChange={(e) => setEquipment(e.target.value)}>
              <option value="">Sin especificar</option>
              {EQUIPMENT_OPTIONS.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </label>

          <div className="ce-toggles">
            <button
              type="button"
              role="switch"
              aria-checked={usesBodyweight}
              className={`ex-chip${usesBodyweight ? " on" : ""}`}
              onClick={() => setUsesBodyweight((v) => !v)}
            >
              Usa peso corporal
            </button>
            <button
              type="button"
              role="switch"
              aria-checked={unilateral}
              className={`ex-chip${unilateral ? " on" : ""}`}
              onClick={() => setUnilateral((v) => !v)}
            >
              Unilateral
            </button>
          </div>

          <label className="ce-field">
            <span className="muted">Instrucciones (un paso por línea, opcional)</span>
            <textarea
              rows={5}
              value={instructions}
              placeholder={"Siéntate con la espalda apoyada\nEmpuja hasta extender los brazos"}
              onChange={(e) => setInstructions(e.target.value)}
            />
          </label>

          {error && <p className="error">{error}</p>}
        </div>
        <div className="sheet-foot">
          <button type="button" className="wk-primary" disabled={busy} onClick={() => void submit()}>
            {busy ? "Creando…" : "Crear ejercicio"}
          </button>
        </div>
      </div>
    </div>
  );
}
