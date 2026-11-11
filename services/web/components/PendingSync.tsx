"use client";

import { useEffect, useState } from "react";

import { readToken } from "@/lib/useToken";
import { flushPending } from "@/lib/workout/sync";

/** Reintenta los entrenos pendientes al cargar la app y al recuperar conexión. */
export function PendingSync() {
  const [rejected, setRejected] = useState<string[]>([]);

  useEffect(() => {
    const run = () => {
      const token = readToken();
      if (!token) return;
      void flushPending(token).then((r) => {
        if (r.rejected.length > 0) setRejected((prev) => [...prev, ...r.rejected]);
      });
    };
    run();
    window.addEventListener("online", run);
    return () => window.removeEventListener("online", run);
  }, []);

  if (rejected.length === 0) return null;
  return (
    <div className="pending-error" role="alert">
      <div>
        <strong>No se pudo guardar un entreno pendiente:</strong>
        <ul>
          {rejected.map((msg, i) => (
            <li key={i}>{msg}</li>
          ))}
        </ul>
      </div>
      <button type="button" onClick={() => setRejected([])}>
        Entendido
      </button>
    </div>
  );
}
