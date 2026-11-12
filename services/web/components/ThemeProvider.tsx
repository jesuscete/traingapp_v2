"use client";

import { useEffect } from "react";

import { applyTheme, getThemePrefs } from "@/lib/theme";

/** Aplica el tema y, en modo automático, lo cambia si el sistema pasa de claro a oscuro. */
export function ThemeProvider() {
  useEffect(() => {
    applyTheme();
    const media = window.matchMedia("(prefers-color-scheme: light)");
    const onChange = () => {
      if (getThemePrefs().mode === "auto") applyTheme();
    };
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);

  return null;
}
