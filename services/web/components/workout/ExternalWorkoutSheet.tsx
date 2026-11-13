"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ChevronRight, FileUp, RefreshCw, Watch } from "lucide-react";

import { Sheet } from "@/components/nutrition/Sheet";
import { api } from "@/lib/api";
import type { GarminStatus } from "@/lib/types";

type SyncState =
  | { kind: "idle" }
  | { kind: "busy" }
  | { kind: "done"; text: string; imported: number }
  | { kind: "error"; text: string };

function syncText(imported: number, skipped: number, errors: number): string {
  if (imported === 0 && errors === 0) return "No hay actividades nuevas en el reloj.";
  return (
    `${imported} actividad${imported === 1 ? "" : "es"} nueva${imported === 1 ? "" : "s"}` +
    (skipped ? `, ${skipped} ya estaba${skipped === 1 ? "" : "n"}` : "") +
    (errors ? `, ${errors} con error` : "") +
    "."
  );
}

export function ExternalWorkoutSheet({ token, onClose }: { token: string; onClose: () => void }) {
  const [garmin, setGarmin] = useState<GarminStatus | null>(null);
  const [sync, setSync] = useState<SyncState>({ kind: "idle" });

  useEffect(() => {
    api
      .garminStatus(token)
      .then(setGarmin)
      .catch(() => setGarmin(null));
  }, [token]);

  async function syncWatch() {
    setSync({ kind: "busy" });
    try {
      const r = await api.garminSync(token);
      setGarmin(r.status);
      setSync({ kind: "done", text: syncText(r.imported, r.skipped, r.errors), imported: r.imported });
    } catch (err) {
      setSync({ kind: "error", text: err instanceof Error ? err.message : "No se pudo sincronizar" });
    }
  }

  const connected = garmin?.connected === true;

  const watchOption = connected ? (
    <li>
      <button type="button" className="ext-option" onClick={syncWatch} disabled={sync.kind === "busy"}>
        <RefreshCw size={22} strokeWidth={1.75} aria-hidden="true" className={sync.kind === "busy" ? "spin" : undefined} />
        <span>
          <strong>{sync.kind === "busy" ? "Sincronizando…" : "Sincronizar reloj"}</strong>
          <span className="muted">Garmin · trae tus últimas actividades</span>
        </span>
      </button>
      {sync.kind === "done" && (
        <p className="ext-result" role="status">
          {sync.text}{" "}
          {sync.imported > 0 && <Link href="/rutinas?tab=historial">Ver historial</Link>}
        </p>
      )}
      {sync.kind === "error" && (
        <p className="error ext-result" role="alert">
          {sync.text}
        </p>
      )}
    </li>
  ) : (
    <li>
      <Link className="ext-option" href="/cuenta/conexiones">
        <Watch size={22} strokeWidth={1.75} aria-hidden="true" />
        <span>
          <strong>Conectar reloj</strong>
          <span className="muted">Garmin · se sincroniza solo</span>
        </span>
        <ChevronRight size={18} aria-hidden="true" />
      </Link>
    </li>
  );

  const fileOption = (
    <li>
      <Link className="ext-option" href="/importar">
        <FileUp size={22} strokeWidth={1.75} aria-hidden="true" />
        <span>
          <strong>Importar archivo</strong>
          <span className="muted">.fit, .gpx o .tcx de tu reloj o app</span>
        </span>
        <ChevronRight size={18} aria-hidden="true" />
      </Link>
    </li>
  );

  return (
    <Sheet title="Cargar entreno externo" onClose={onClose} compact>
      <ul className="ext-options">
        {/* Lo que el usuario tiene configurado va primero: así es un toque. */}
        {connected ? watchOption : fileOption}
        {connected ? fileOption : watchOption}
      </ul>
    </Sheet>
  );
}
