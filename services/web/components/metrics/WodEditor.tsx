"use client";

import { useEffect, useMemo, useState } from "react";

import { exerciseDisplayName, normalizeText, searchText } from "@/lib/exerciseSearch";
import type { CatalogExercise, HyroxCategory, WodFormat } from "@/lib/types";
import { useCatalog } from "@/lib/useCatalog";
import { readToken } from "@/lib/useToken";
import {
  HYROX_CATEGORY_LABELS,
  WOD_FORMAT_HELP,
  WOD_FORMAT_LABELS,
  hyroxTemplate,
  isHyrox,
  newMovement,
  scoreKindFor,
  usesTimeCap,
  type MovementForm,
  type MovementUnit,
  type WodForm,
} from "@/lib/wod";

const CROSSFIT_FORMATS: WodFormat[] = ["for_time", "amrap", "emom", "tabata", "intervals", "strength", "other"];
const HYROX_FORMATS: WodFormat[] = ["hyrox_sim", "hyrox_race", "for_time", "amrap", "emom", "intervals", "other"];
const UNIT_LABELS: Record<MovementUnit, string> = { reps: "reps", distance: "m", calories: "cal" };

type Props = { discipline: string; value: WodForm; onChange: (next: WodForm) => void };

function unitOf(ex: CatalogExercise): MovementUnit {
  return ex.details?.unit ?? "reps";
}

/** Buscador del catálogo para un movimiento: sugiere mientras escribes. */
function MovementPicker({
  movement,
  catalog,
  onChange,
}: {
  movement: MovementForm;
  catalog: { ex: CatalogExercise; haystack: string }[];
  onChange: (changes: Partial<MovementForm>) => void;
}) {
  const [open, setOpen] = useState(false);
  const query = normalizeText(movement.name);
  const matches = useMemo(() => {
    if (query.length < 2 || movement.exerciseId) return [];
    const words = query.split(" ");
    return catalog.filter((c) => words.every((w) => c.haystack.includes(w))).slice(0, 6);
  }, [catalog, query, movement.exerciseId]);

  return (
    <div className="wod-picker">
      <input
        type="text"
        placeholder="Movimiento (ej.: wall ball)"
        value={movement.name}
        onChange={(e) => {
          onChange({ name: e.target.value, exerciseId: null });
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 150)}
        aria-label="Movimiento"
      />
      {open && matches.length > 0 && (
        <ul className="wod-suggest" role="listbox">
          {matches.map(({ ex }) => (
            <li key={ex.id}>
              <button
                type="button"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  onChange({ name: exerciseDisplayName(ex), exerciseId: ex.id, unit: unitOf(ex) });
                  setOpen(false);
                }}
              >
                {exerciseDisplayName(ex)}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function WodEditor({ discipline, value, onChange }: Props) {
  const patch = (changes: Partial<WodForm>) => onChange({ ...value, ...changes });
  const { catalog } = useCatalog(readToken());
  const indexed = useMemo(() => catalog.map((ex) => ({ ex, haystack: searchText(ex) })), [catalog]);
  const formats = discipline === "hyrox" ? HYROX_FORMATS : CROSSFIT_FORMATS;

  // Al cambiar de disciplina, el formato por defecto se adapta si aún no se ha tocado nada.
  useEffect(() => {
    const pristine =
      value.movements.length === 0 && !value.time && !value.rounds && !value.totalReps && !value.load;
    if (value.format !== formats[0] && (pristine || !formats.includes(value.format))) {
      onChange({ ...value, format: formats[0] });
    }
    // solo reacciona al cambio de disciplina
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [discipline]);

  const score = scoreKindFor(value.format);
  const setMovement = (id: string, changes: Partial<MovementForm>) =>
    patch({ movements: value.movements.map((m) => (m.id === id ? { ...m, ...changes } : m)) });

  function loadHyrox(category: HyroxCategory = value.hyroxCategory) {
    if (value.movements.some((m) => m.name.trim()) && !window.confirm("¿Sustituir los movimientos por las estaciones HYROX?")) {
      return;
    }
    patch({ hyroxCategory: category, ...hyroxTemplate(category) });
  }

  return (
    <section className="block m3-block">
      <h2>WOD</h2>
      <div className="m3-row wod-row">
        <label className="m3-field">
          <span>Tipo de entreno</span>
          <select value={value.format} onChange={(e) => patch({ format: e.target.value as WodFormat })}>
            {formats.map((f) => (
              <option key={f} value={f}>
                {WOD_FORMAT_LABELS[f]}
              </option>
            ))}
          </select>
        </label>
        <label className="m3-field">
          <span>Nombre (opcional)</span>
          <input
            type="text"
            maxLength={80}
            placeholder={isHyrox(value.format) ? "HYROX Madrid" : "Fran, Murph…"}
            value={value.name}
            onChange={(e) => patch({ name: e.target.value })}
          />
        </label>
      </div>
      <p className="muted m3-hint">{WOD_FORMAT_HELP[value.format]}</p>

      {isHyrox(value.format) && (
        <div className="m3-row wod-row">
          <label className="m3-field">
            <span>Categoría</span>
            <select
              value={value.hyroxCategory}
              onChange={(e) => patch({ hyroxCategory: e.target.value as HyroxCategory })}
            >
              {(Object.keys(HYROX_CATEGORY_LABELS) as HyroxCategory[]).map((c) => (
                <option key={c} value={c}>
                  {HYROX_CATEGORY_LABELS[c]}
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="secondary wod-hyrox-btn" onClick={() => loadHyrox()}>
            Cargar estaciones HYROX
          </button>
        </div>
      )}

      <div className="m3-row wod-row">
        {!isHyrox(value.format) && value.format !== "strength" && (
          <label className="m3-field">
            <span>Esquema (opcional)</span>
            <input
              type="text"
              maxLength={60}
              placeholder={value.format === "for_time" ? "21-15-9 · 5 rondas" : "3 bloques"}
              value={value.scheme}
              onChange={(e) => patch({ scheme: e.target.value })}
            />
          </label>
        )}
        {usesTimeCap(value.format) && (
          <label className="m3-field">
            <span>{value.format === "amrap" || value.format === "emom" ? "Duración (min)" : "Time cap (min)"}</span>
            <input
              type="text"
              inputMode="decimal"
              value={value.timeCap}
              onChange={(e) => patch({ timeCap: e.target.value })}
            />
          </label>
        )}
      </div>

      <h3 className="wod-sub">Resultado</h3>
      <div className="m3-row wod-row">
        {score === "time" && !value.capped && (
          <label className="m3-field">
            <span>Tiempo (mm:ss)</span>
            <input
              type="text"
              inputMode="numeric"
              placeholder={isHyrox(value.format) ? "1:15:30" : "8:42"}
              value={value.time}
              onChange={(e) => patch({ time: e.target.value })}
            />
          </label>
        )}
        {score === "rounds" && (
          <>
            <label className="m3-field">
              <span>Rondas</span>
              <input type="text" inputMode="numeric" value={value.rounds} onChange={(e) => patch({ rounds: e.target.value })} />
            </label>
            <label className="m3-field">
              <span>+ reps</span>
              <input
                type="text"
                inputMode="numeric"
                value={value.extraReps}
                onChange={(e) => patch({ extraReps: e.target.value })}
              />
            </label>
          </>
        )}
        {(score === "reps" || (score === "time" && value.capped)) && (
          <label className="m3-field">
            <span>{value.capped ? "Reps hechas al time cap" : "Reps totales"}</span>
            <input
              type="text"
              inputMode="numeric"
              value={value.totalReps}
              onChange={(e) => patch({ totalReps: e.target.value })}
            />
          </label>
        )}
        {score === "load" && (
          <label className="m3-field">
            <span>Carga máxima (kg)</span>
            <input type="text" inputMode="decimal" value={value.load} onChange={(e) => patch({ load: e.target.value })} />
          </label>
        )}
      </div>
      <div className="wod-toggles">
        <button
          type="button"
          className={`m3-sent${value.rx ? " on" : ""}`}
          aria-pressed={value.rx}
          onClick={() => patch({ rx: !value.rx })}
        >
          {value.rx ? "Rx" : "Scaled"}
        </button>
        {score === "time" && (
          <label className="wod-check">
            <input type="checkbox" checked={value.capped} onChange={(e) => patch({ capped: e.target.checked })} />
            No terminé (time cap)
          </label>
        )}
      </div>

      <h3 className="wod-sub">Movimientos</h3>
      {value.movements.map((m) => (
        <div key={m.id} className="m3-card wod-move">
          <MovementPicker movement={m} catalog={indexed} onChange={(c) => setMovement(m.id, c)} />
          <div className="wod-move-row">
            <input
              type="text"
              inputMode="decimal"
              aria-label="Cantidad"
              placeholder="Cant."
              value={m.amount}
              onChange={(e) => setMovement(m.id, { amount: e.target.value })}
            />
            <select
              aria-label="Unidad"
              value={m.unit}
              onChange={(e) => setMovement(m.id, { unit: e.target.value as MovementUnit })}
            >
              {(Object.keys(UNIT_LABELS) as MovementUnit[]).map((u) => (
                <option key={u} value={u}>
                  {UNIT_LABELS[u]}
                </option>
              ))}
            </select>
            <input
              type="text"
              inputMode="decimal"
              aria-label="Peso en kg"
              placeholder="kg"
              value={m.weight}
              onChange={(e) => setMovement(m.id, { weight: e.target.value })}
            />
            <button
              type="button"
              className="secondary"
              aria-label={`Quitar ${m.name || "movimiento"}`}
              onClick={() => patch({ movements: value.movements.filter((x) => x.id !== m.id) })}
            >
              ✕
            </button>
          </div>
        </div>
      ))}
      <button
        type="button"
        className="secondary m3-wide"
        disabled={value.movements.length >= 30}
        onClick={() => patch({ movements: [...value.movements, newMovement()] })}
      >
        + Añadir movimiento
      </button>

      {isHyrox(value.format) && value.splits.length > 0 && (
        <>
          <h3 className="wod-sub">Tiempos por tramo (opcional)</h3>
          <p className="muted m3-hint">Si los rellenas, el tiempo total se calcula solo.</p>
          <div className="wod-splits">
            {value.splits.map((s) => (
              <label key={s.id} className="m3-field">
                <span>{s.name}</span>
                <input
                  type="text"
                  inputMode="numeric"
                  placeholder="mm:ss"
                  value={s.time}
                  onChange={(e) =>
                    patch({ splits: value.splits.map((x) => (x.id === s.id ? { ...x, time: e.target.value } : x)) })
                  }
                />
              </label>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
