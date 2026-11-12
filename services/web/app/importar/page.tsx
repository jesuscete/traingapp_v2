"use client";

import Link from "next/link";
import { useRef, useState } from "react";

import { BottomNav } from "@/components/BottomNav";
import { api } from "@/lib/api";
import { translateDiscipline } from "@/lib/labels";
import type { ImportResult } from "@/lib/types";
import { useToken } from "@/lib/useToken";

const MAX_BYTES = 15 * 1024 * 1024;
const EXTENSIONS = [".fit", ".gpx", ".tcx"];

type Item = {
  id: number;
  file: File;
  state: "queued" | "uploading" | "done";
  result: ImportResult | null;
  maxHrSaved: boolean;
  maxHrBusy: boolean;
};

const STATUS_LABEL: Record<ImportResult["status"], string> = {
  imported: "Importada",
  duplicate: "Ya importada",
  overlap: "Posible duplicado",
  error: "Error",
};

function errorResult(file: File, message: string): ImportResult {
  return {
    filename: file.name,
    status: "error",
    message,
    sessionId: null,
    discipline: null,
    suggestedMaxHr: null,
  };
}

export default function Importar() {
  const token = useToken();
  const [items, setItems] = useState<Item[]>([]);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const nextId = useRef(1);
  const inputRef = useRef<HTMLInputElement>(null);

  function patch(id: number, change: Partial<Item>) {
    setItems((prev) => prev.map((it) => (it.id === id ? { ...it, ...change } : it)));
  }

  async function upload(item: Item, force: boolean) {
    if (!token) return;
    patch(item.id, { state: "uploading" });
    let result: ImportResult;
    try {
      result = await api.importActivity(token, item.file, force);
    } catch (err) {
      result = errorResult(
        item.file,
        err instanceof Error ? err.message : "No se pudo importar el archivo",
      );
    }
    patch(item.id, { state: "done", result });
  }

  async function addFiles(list: FileList | File[]) {
    if (!token || busy) return;
    const added: Item[] = [];
    for (const file of Array.from(list)) {
      const lower = file.name.toLowerCase();
      const item: Item = {
        id: nextId.current++,
        file,
        state: "queued",
        result: null,
        maxHrSaved: false,
        maxHrBusy: false,
      };
      if (!EXTENSIONS.some((ext) => lower.endsWith(ext))) {
        item.state = "done";
        item.result = errorResult(file, "Formato no admitido (usa .fit, .gpx o .tcx)");
      } else if (file.size > MAX_BYTES) {
        item.state = "done";
        item.result = errorResult(file, "El archivo supera los 15 MB");
      }
      added.push(item);
    }
    if (added.length === 0) return;
    setItems((prev) => [...added, ...prev]);
    setBusy(true);
    try {
      for (const item of added) {
        if (item.state === "queued") await upload(item, false);
      }
    } finally {
      setBusy(false);
    }
  }

  async function forceImport(item: Item) {
    setBusy(true);
    try {
      await upload(item, true);
    } finally {
      setBusy(false);
    }
  }

  async function updateMaxHr(item: Item, value: number) {
    if (!token) return;
    patch(item.id, { maxHrBusy: true });
    try {
      await api.updateProfile(token, { maxHr: value });
      patch(item.id, { maxHrSaved: true, maxHrBusy: false });
    } catch {
      patch(item.id, { maxHrBusy: false });
    }
  }

  const doneCount = items.filter((i) => i.state === "done").length;

  return (
    <main className="dashboard">
      <BottomNav />
      <section className="welcome">
        <h2>Importar actividad</h2>
        <p className="subtitle">
          Sube las actividades de tu reloj en formato .fit, .gpx o .tcx.
        </p>
      </section>

      {!token ? (
        <p className="muted">Cargando...</p>
      ) : (
        <>
          <section className="block m3-block">
            <div
              className={`imp-drop${dragging ? " dragging" : ""}`}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                void addFiles(e.dataTransfer.files);
              }}
            >
              <input
                ref={inputRef}
                type="file"
                accept=".fit,.gpx,.tcx"
                multiple
                hidden
                onChange={(e) => {
                  if (e.target.files) void addFiles(e.target.files);
                  e.target.value = "";
                }}
              />
              <button
                type="button"
                className="imp-pick"
                disabled={busy}
                onClick={() => inputRef.current?.click()}
              >
                {busy ? "Importando..." : "Elegir archivos"}
              </button>
              <p className="muted">o arrástralos aquí (.fit, .gpx, .tcx · máx. 15 MB)</p>
            </div>
            <p className="muted imp-help">
              Exporta la actividad desde Garmin Connect (⚙ → Exportar original = .fit) o desde
              tu app/reloj como GPX/TCX.
            </p>
          </section>

          {items.length > 0 && (
            <section className="block">
              <h2>
                Resultados{" "}
                <span className="muted">
                  ({doneCount}/{items.length})
                </span>
              </h2>
              <ul className="imp-list">
                {items.map((item) => {
                  const r = item.result;
                  return (
                    <li key={item.id} className="imp-item">
                      <div className="imp-head">
                        <strong className="imp-name">{item.file.name}</strong>
                        {item.state === "queued" && <span className="imp-badge">En cola</span>}
                        {item.state === "uploading" && (
                          <span className="imp-badge">Subiendo...</span>
                        )}
                        {r && (
                          <span className={`imp-badge ${r.status}`}>{STATUS_LABEL[r.status]}</span>
                        )}
                      </div>
                      {r && (
                        <>
                          <p className={r.status === "error" ? "error" : "muted"}>
                            {r.message}
                            {r.discipline && r.status === "imported"
                              ? ` · ${translateDiscipline(r.discipline)}`
                              : ""}
                          </p>
                          <div className="imp-actions">
                            {r.sessionId && (
                              <Link className="imp-link" href={`/entrenos/${r.sessionId}`}>
                                {r.status === "overlap" ? "Ver la sesión existente" : "Ver sesión"}
                              </Link>
                            )}
                            {r.status === "overlap" && (
                              <button
                                type="button"
                                className="secondary imp-btn"
                                disabled={busy}
                                onClick={() => void forceImport(item)}
                              >
                                Importar igualmente
                              </button>
                            )}
                            {r.suggestedMaxHr != null &&
                              (item.maxHrSaved ? (
                                <span className="ok">FC máxima actualizada</span>
                              ) : (
                                <button
                                  type="button"
                                  className="secondary imp-btn"
                                  disabled={item.maxHrBusy}
                                  onClick={() => void updateMaxHr(item, r.suggestedMaxHr as number)}
                                >
                                  Actualizar FC máxima a {r.suggestedMaxHr}
                                </button>
                              ))}
                          </div>
                        </>
                      )}
                    </li>
                  );
                })}
              </ul>
            </section>
          )}
        </>
      )}
    </main>
  );
}
