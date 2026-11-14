"use client";

import { useEffect } from "react";

import { applyTheme } from "@/lib/theme";

/** Aplica el tema guardado al montar (por si el script de arranque no pudo). */
export function ThemeProvider() {
  useEffect(() => {
    applyTheme();
  }, []);

  return null;
}
