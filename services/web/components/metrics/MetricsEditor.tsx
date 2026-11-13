"use client";

import {
  BLOCK_TYPES,
  BLOCK_TYPE_LABELS,
  BOULDER_GRADES,
  CLIMBING_STYLES,
  CLIMBING_STYLE_LABELS,
  ROUTE_GRADES,
  blockMinutes,
  formatPaceText,
  newBlock,
  newRoute,
  totalCombatMinutes,
  type BlockForm,
  type MetricsForm,
  type MetricsKind,
  type RouteForm,
} from "@/lib/metrics";
import type { ClimbingStyle, CombatBlockType } from "@/lib/types";
import { WodEditor } from "@/components/metrics/WodEditor";

type Props = {
  kind: MetricsKind;
  discipline: string;
  value: MetricsForm;
  onChange: (next: MetricsForm) => void;
  durationMinutes: string;
};

function fmtMin(n: number): string {
  return String(Number(n.toFixed(1)));
}

export function MetricsEditor({ kind, discipline, value, onChange, durationMinutes }: Props) {
  const patch = (changes: Partial<MetricsForm>) => onChange({ ...value, ...changes });

  if (kind === "wod") {
    return <WodEditor discipline={discipline} value={value.wod} onChange={(wod) => patch({ wod })} />;
  }

  if (kind === "combat") {
    const setBlock = (id: string, changes: Partial<BlockForm>) =>
      patch({ blocks: value.blocks.map((b) => (b.id === id ? { ...b, ...changes } : b)) });
    const duplicate = (block: BlockForm) => {
      const index = value.blocks.findIndex((b) => b.id === block.id);
      const copy: BlockForm = { ...block, id: newBlock().id };
      const blocks = [...value.blocks];
      blocks.splice(index + 1, 0, copy);
      patch({ blocks });
    };
    return (
      <section className="block m3-block">
        <h2>Bloques de entrenamiento</h2>
        {value.blocks.map((block, index) => (
          <div key={block.id} className="m3-card">
            <div className="m3-card-head">
              <strong>Bloque {index + 1}</strong>
              <span className="muted">{fmtMin(blockMinutes(block))} min</span>
            </div>
            <label className="m3-field">
              <span>Tipo</span>
              <select
                value={block.type}
                onChange={(e) => setBlock(block.id, { type: e.target.value as CombatBlockType })}
              >
                {BLOCK_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {BLOCK_TYPE_LABELS[t]}
                  </option>
                ))}
              </select>
            </label>
            <div className="m3-toggle" role="group" aria-label="Modo del bloque">
              <button
                type="button"
                className={block.mode === "rounds" ? "on" : ""}
                onClick={() => setBlock(block.id, { mode: "rounds" })}
              >
                Rounds
              </button>
              <button
                type="button"
                className={block.mode === "minutes" ? "on" : ""}
                onClick={() => setBlock(block.id, { mode: "minutes" })}
              >
                Minutos
              </button>
            </div>
            {block.mode === "rounds" ? (
              <div className="m3-row">
                <label className="m3-field">
                  <span>Rounds</span>
                  <input
                    type="number"
                    inputMode="numeric"
                    min={1}
                    max={50}
                    value={block.rounds}
                    onChange={(e) => setBlock(block.id, { rounds: e.target.value })}
                  />
                </label>
                <label className="m3-field">
                  <span>Duración (m:ss)</span>
                  <input
                    type="text"
                    inputMode="numeric"
                    placeholder="3:00"
                    value={block.roundTime}
                    onChange={(e) => setBlock(block.id, { roundTime: e.target.value })}
                  />
                </label>
              </div>
            ) : (
              <label className="m3-field">
                <span>Minutos</span>
                <input
                  type="number"
                  inputMode="decimal"
                  min={1}
                  max={300}
                  value={block.minutes}
                  onChange={(e) => setBlock(block.id, { minutes: e.target.value })}
                />
              </label>
            )}
            <label className="m3-field">
              <span>Golpes (opcional)</span>
              <input
                type="number"
                inputMode="numeric"
                min={0}
                value={block.strikes}
                onChange={(e) => setBlock(block.id, { strikes: e.target.value })}
              />
            </label>
            <div className="m3-actions">
              <button type="button" className="secondary" onClick={() => duplicate(block)}>
                Duplicar
              </button>
              <button
                type="button"
                className="secondary"
                disabled={value.blocks.length <= 1}
                onClick={() => patch({ blocks: value.blocks.filter((b) => b.id !== block.id) })}
              >
                Quitar
              </button>
            </div>
          </div>
        ))}
        <button
          type="button"
          className="secondary m3-wide"
          disabled={value.blocks.length >= 20}
          onClick={() => patch({ blocks: [...value.blocks, newBlock()] })}
        >
          + Añadir bloque
        </button>
        <p className="m3-total">
          Total: <strong>{fmtMin(totalCombatMinutes(value.blocks))} min</strong>
        </p>
      </section>
    );
  }

  if (kind === "endurance") {
    const km = Number(value.distanceKm.replace(",", "."));
    const minutes = Number(durationMinutes.replace(",", "."));
    const pace = formatPaceText(
      discipline,
      Number.isFinite(km) && km > 0 ? km * 1000 : null,
      Number.isFinite(minutes) && minutes > 0 ? minutes : null,
    );
    return (
      <section className="block m3-block">
        <h2>Datos de resistencia</h2>
        <label className="m3-field">
          <span>Distancia (km)</span>
          <input
            type="number"
            inputMode="decimal"
            min={0}
            step="0.01"
            value={value.distanceKm}
            onChange={(e) => patch({ distanceKm: e.target.value })}
          />
        </label>
        {pace && (
          <p className="m3-total">
            Ritmo: <strong>{pace}</strong>
          </p>
        )}
        <div className="m3-row">
          <label className="m3-field">
            <span>FC media</span>
            <input
              type="number"
              inputMode="numeric"
              min={30}
              max={230}
              value={value.avgHr}
              onChange={(e) => patch({ avgHr: e.target.value })}
            />
          </label>
          <label className="m3-field">
            <span>FC máxima</span>
            <input
              type="number"
              inputMode="numeric"
              min={30}
              max={240}
              value={value.maxHr}
              onChange={(e) => patch({ maxHr: e.target.value })}
            />
          </label>
        </div>
        <label className="m3-field">
          <span>Desnivel positivo (m)</span>
          <input
            type="number"
            inputMode="numeric"
            min={0}
            value={value.elevation}
            onChange={(e) => patch({ elevation: e.target.value })}
          />
        </label>
      </section>
    );
  }

  if (kind === "climbing") {
    const setRoute = (id: string, changes: Partial<RouteForm>) =>
      patch({ routes: value.routes.map((r) => (r.id === id ? { ...r, ...changes } : r)) });
    const grades = value.style === "boulder" ? BOULDER_GRADES : ROUTE_GRADES;
    return (
      <section className="block m3-block">
        <h2>Escalada</h2>
        <label className="m3-field">
          <span>Estilo</span>
          <select
            value={value.style}
            onChange={(e) => patch({ style: e.target.value as ClimbingStyle })}
          >
            {CLIMBING_STYLES.map((s) => (
              <option key={s} value={s}>
                {CLIMBING_STYLE_LABELS[s]}
              </option>
            ))}
          </select>
        </label>
        <p className="muted m3-hint">Toca un grado para añadir una vía encadenada:</p>
        <div className="m3-chips">
          {grades.map((g) => (
            <button
              key={g}
              type="button"
              className="m3-chip"
              disabled={value.routes.length >= 100}
              onClick={() => patch({ routes: [...value.routes, newRoute(g)] })}
            >
              {g}
            </button>
          ))}
        </div>
        {value.routes.map((route, index) => (
          <div key={route.id} className="m3-card m3-route">
            <div className="m3-row">
              <label className="m3-field">
                <span>Vía {index + 1} · grado</span>
                <input
                  type="text"
                  maxLength={12}
                  value={route.grade}
                  onChange={(e) => setRoute(route.id, { grade: e.target.value })}
                />
              </label>
              <label className="m3-field">
                <span>Intentos</span>
                <input
                  type="number"
                  inputMode="numeric"
                  min={1}
                  max={100}
                  value={route.attempts}
                  onChange={(e) => setRoute(route.id, { attempts: e.target.value })}
                />
              </label>
            </div>
            <div className="m3-actions">
              <button
                type="button"
                className={`m3-sent${route.sent ? " on" : ""}`}
                aria-pressed={route.sent}
                onClick={() => setRoute(route.id, { sent: !route.sent })}
              >
                {route.sent ? "Encadenada" : "No encadenada"}
              </button>
              <button
                type="button"
                className="secondary"
                onClick={() => patch({ routes: value.routes.filter((r) => r.id !== route.id) })}
              >
                Quitar
              </button>
            </div>
          </div>
        ))}
        <button
          type="button"
          className="secondary m3-wide"
          disabled={value.routes.length >= 100}
          onClick={() => patch({ routes: [...value.routes, newRoute("")] })}
        >
          + Añadir vía
        </button>
      </section>
    );
  }

  return (
    <section className="block m3-block">
      <h2>Notas de la actividad</h2>
      <label className="m3-field">
        <span>Notas ({value.notes.length}/500)</span>
        <textarea
          rows={3}
          maxLength={500}
          value={value.notes}
          onChange={(e) => patch({ notes: e.target.value })}
        />
      </label>
    </section>
  );
}
