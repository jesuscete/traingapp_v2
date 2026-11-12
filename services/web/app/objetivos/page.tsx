"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  Check,
  ChevronRight,
  Pencil,
  Scale,
  Star,
  Trash2,
} from "lucide-react";

import { BottomNav } from "@/components/BottomNav";
import { api } from "@/lib/api";
import type { Goal, GoalIn, GoalKind } from "@/lib/types";
import { GOAL_KIND_LABELS, GoalKindIcon, countdownLabel } from "@/components/goals";
import { MAIN_SPORTS, OTHER_SPORTS } from "@/lib/sports";
import { useToken } from "@/lib/useToken";

type FormState = {
  kind: GoalKind;
  title: string;
  sport: string;
  targetDate: string;
  targetValue: string;
  unit: string;
  notes: string;
  isPrimary: boolean;
};

const EMPTY_FORM: FormState = {
  kind: "event",
  title: "",
  sport: "",
  targetDate: "",
  targetValue: "",
  unit: "",
  notes: "",
  isPrimary: false,
};

function toForm(g: Goal): FormState {
  return {
    kind: g.kind,
    title: g.title,
    sport: g.sport ?? "",
    targetDate: g.targetDate ?? "",
    targetValue: g.targetValue != null ? String(g.targetValue) : "",
    unit: g.unit ?? "",
    notes: g.notes ?? "",
    isPrimary: g.isPrimary ?? false,
  };
}

export default function Objetivos() {
  const token = useToken();
  const [goals, setGoals] = useState<Goal[]>([]);
  const [primarySport, setPrimarySport] = useState<string | null>(null);
  const [sports, setSports] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<Goal | "new" | null>(null);
  const [form, setForm] = useState<FormState>(EMPTY_FORM);

  const load = useCallback(async (tk: string) => {
    try {
      const [g, p] = await Promise.all([api.listGoals(tk), api.getProfile(tk)]);
      setGoals(g);
      setPrimarySport(p.primarySport ?? null);
      setSports(p.sports ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (token) void load(token);
  }, [token, load]);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar");
    } finally {
      setBusy(false);
    }
  }

  function choosePrimary(key: string) {
    if (!token) return;
    const previous = primarySport;
    setPrimarySport(key);
    void run(async () => {
      try {
        await api.updateProfile(token, { primarySport: key });
      } catch (err) {
        setPrimarySport(previous);
        throw err;
      }
    });
  }

  function toggleOther(key: string) {
    if (!token) return;
    const previous = sports;
    const next = previous.includes(key) ? previous.filter((s) => s !== key) : [...previous, key];
    setSports(next);
    void run(async () => {
      try {
        await api.updateProfile(token, { sports: next });
      } catch (err) {
        setSports(previous);
        throw err;
      }
    });
  }

  function openForm(goal: Goal | "new") {
    setEditing(goal);
    setForm(goal === "new" ? EMPTY_FORM : toForm(goal));
  }

  function buildBody(f: FormState, extra: Partial<GoalIn> = {}): GoalIn {
    const value = f.targetValue.trim() === "" ? null : Number(f.targetValue.replace(",", "."));
    return {
      kind: f.kind,
      title: f.title.trim(),
      sport: f.sport || null,
      targetDate: f.targetDate || null,
      targetValue: value != null && Number.isFinite(value) ? value : null,
      unit: f.unit.trim() || null,
      notes: f.notes.trim() || null,
      isPrimary: f.isPrimary,
      ...extra,
    };
  }

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (!token || !editing || form.title.trim() === "") return;
    void run(async () => {
      const body = buildBody(form, editing !== "new" ? { done: editing.done ?? false } : {});
      if (editing === "new") await api.createGoal(token, body);
      else await api.updateGoal(token, editing.id, body);
      setEditing(null);
      await load(token);
    });
  }

  function toggleDone(goal: Goal) {
    if (!token) return;
    void run(async () => {
      await api.updateGoal(token, goal.id, buildBody(toForm(goal), { done: !goal.done }));
      await load(token);
    });
  }

  function remove(goal: Goal) {
    if (!token || !window.confirm(`¿Eliminar el objetivo "${goal.title}"?`)) return;
    void run(async () => {
      await api.deleteGoal(token, goal.id);
      await load(token);
    });
  }

  const active = goals.filter((g) => !g.done);
  const done = goals.filter((g) => g.done);

  function GoalRow({ goal }: { goal: Goal }) {
    const count = goal.done ? null : countdownLabel(goal.daysLeft);
    return (
      <div className={`ob-goal${goal.isPrimary ? " primary" : ""}${goal.done ? " done" : ""}`}>
        <span className="hub-icon">
          <GoalKindIcon kind={goal.kind} />
        </span>
        <div className="ob-goal-body">
          <strong>
            {goal.title}
            {goal.isPrimary && (
              <Star
                size={14}
                strokeWidth={1.75}
                fill="currentColor"
                style={{ marginLeft: 6, color: "#f5b942", verticalAlign: "-1px" }}
                aria-label="Objetivo principal"
              />
            )}
          </strong>
          <span className="muted">
            {GOAL_KIND_LABELS[goal.kind]}
            {goal.targetValue != null ? ` · ${goal.targetValue}${goal.unit ? ` ${goal.unit}` : ""}` : ""}
            {goal.targetDate ? ` · ${goal.targetDate}` : ""}
            {count ? ` · ${count}` : ""}
          </span>
          {goal.notes && <span className="muted" style={{ display: "block" }}>{goal.notes}</span>}
          <div className="ob-row" style={{ marginTop: "0.4rem" }}>
            <button type="button" className="secondary" disabled={busy} onClick={() => toggleDone(goal)}>
              <Check size={14} strokeWidth={1.75} aria-hidden="true" /> {goal.done ? "Reabrir" : "Hecho"}
            </button>
            <button type="button" className="secondary" disabled={busy} onClick={() => openForm(goal)}>
              <Pencil size={14} strokeWidth={1.75} aria-hidden="true" /> Editar
            </button>
            <button type="button" className="link" disabled={busy} onClick={() => remove(goal)}>
              <Trash2 size={14} strokeWidth={1.75} aria-hidden="true" /> Borrar
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!token) return null;

  return (
    <main className="dashboard">
      <BottomNav />
      <section className="welcome">
        <h2>Objetivos y deporte</h2>
        <p className="subtitle">Define qué buscas y en qué deporte te preparas.</p>
      </section>

      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">Cargando...</p>}

      {!loading && (
        <>
          <section className="ob-section">
            <h2>Deporte principal</h2>
            <p className="muted">
              El análisis de preparación y el entrenador IA se adaptan a tu deporte principal.
            </p>
            <div className="chips">
              {MAIN_SPORTS.map((s) => (
                <button
                  key={s.key}
                  type="button"
                  disabled={busy}
                  className={`chip chip-toggle${primarySport === s.key ? " on" : ""}`}
                  onClick={() => choosePrimary(s.key)}
                >
                  {s.label}
                </button>
              ))}
              <button
                type="button"
                disabled={busy}
                className={`chip chip-toggle${
                  primarySport && !MAIN_SPORTS.some((s) => s.key === primarySport) ? " on" : ""
                }`}
                onClick={() => choosePrimary("otro")}
              >
                Otro…
              </button>
            </div>
            <h3 style={{ marginTop: "1rem", fontSize: "0.95rem" }}>Otros deportes</h3>
            <div className="chips">
              {OTHER_SPORTS.map((s) => (
                <button
                  key={s.key}
                  type="button"
                  disabled={busy}
                  className={`chip chip-toggle${sports.includes(s.key) ? " on" : ""}`}
                  onClick={() => toggleOther(s.key)}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </section>

          <section className="ob-section">
            <h2>Objetivos</h2>
            {active.length === 0 && editing === null && (
              <p className="muted">Aún no tienes objetivos activos.</p>
            )}
            {active.map((g) => (
              <GoalRow key={g.id} goal={g} />
            ))}

            {editing === null ? (
              <div className="chat-actions">
                <button type="button" onClick={() => openForm("new")}>
                  + Nuevo objetivo
                </button>
              </div>
            ) : (
              <form className="ob-form" onSubmit={submit}>
                <label>
                  Tipo
                  <select
                    value={form.kind}
                    onChange={(e) => setForm({ ...form, kind: e.target.value as GoalKind })}
                  >
                    {(Object.keys(GOAL_KIND_LABELS) as GoalKind[]).map((k) => (
                      <option key={k} value={k}>
                        {GOAL_KIND_LABELS[k]}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Título
                  <input
                    value={form.title}
                    required
                    maxLength={120}
                    placeholder="p. ej. Combate amateur en marzo"
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                  />
                </label>
                <label>
                  Deporte (opcional)
                  <select value={form.sport} onChange={(e) => setForm({ ...form, sport: e.target.value })}>
                    <option value="">—</option>
                    {OTHER_SPORTS.map((s) => (
                      <option key={s.key} value={s.key}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Fecha objetivo
                  <input
                    type="date"
                    value={form.targetDate}
                    onChange={(e) => setForm({ ...form, targetDate: e.target.value })}
                  />
                </label>
                <div className="ob-row">
                  <label style={{ flex: 1 }}>
                    Valor objetivo
                    <input
                      inputMode="decimal"
                      value={form.targetValue}
                      onChange={(e) => setForm({ ...form, targetValue: e.target.value })}
                    />
                  </label>
                  <label style={{ flex: 1 }}>
                    Unidad
                    <input
                      value={form.unit}
                      placeholder="kg, min, km…"
                      onChange={(e) => setForm({ ...form, unit: e.target.value })}
                    />
                  </label>
                </div>
                <label>
                  Notas
                  <textarea
                    rows={2}
                    value={form.notes}
                    onChange={(e) => setForm({ ...form, notes: e.target.value })}
                  />
                </label>
                <label style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                  <input
                    type="checkbox"
                    checked={form.isPrimary}
                    onChange={(e) => setForm({ ...form, isPrimary: e.target.checked })}
                  />
                  Objetivo principal
                </label>
                <div className="ob-row">
                  <button type="submit" disabled={busy || form.title.trim() === ""}>
                    Guardar
                  </button>
                  <button type="button" className="secondary" onClick={() => setEditing(null)}>
                    Cancelar
                  </button>
                </div>
              </form>
            )}

            {done.length > 0 && (
              <details style={{ marginTop: "0.8rem" }}>
                <summary className="muted">Completados ({done.length})</summary>
                {done.map((g) => (
                  <GoalRow key={g.id} goal={g} />
                ))}
              </details>
            )}
          </section>

          <div className="hub-grid hub-list">
          <Link className="hub-tile" href="/comidas#objetivo">
            <span className="hub-icon">
              <Scale size={22} strokeWidth={1.75} aria-hidden="true" />
            </span>
            <span className="hub-text">
              <span className="hub-label">Objetivo de peso y nutrición</span>
              <span className="hub-sub">Calorías, proteína y peso objetivo</span>
            </span>
            <ChevronRight className="hub-chev" size={18} strokeWidth={1.75} aria-hidden="true" />
          </Link>
          </div>
        </>
      )}
    </main>
  );
}
