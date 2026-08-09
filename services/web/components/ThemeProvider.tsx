"use client";

import { useEffect } from "react";

import { getTheme } from "@/lib/theme";

export function ThemeProvider() {
  useEffect(() => {
    const saved = getTheme();
    if (saved) {
      document.documentElement.dataset.theme = saved;
    }
  }, []);

  return null;
}
