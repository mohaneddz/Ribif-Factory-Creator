"use client";

import { useEffect, useState } from "react";
import { getTheme, ThemeMode } from "@/utils/theme";

const applyTheme = (mode: ThemeMode) => {
  const root = document.documentElement;
  // Use standard 'dark' class for Tailwind
  if (mode === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
};

export default function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>("light");

  useEffect(() => {
    const mode = getTheme();
    // localStorage is only readable after mount
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setThemeState(mode);
    applyTheme(mode);

    const handler = (event: Event) => {
      if (!(event instanceof CustomEvent)) return;
      const next = (event.detail as ThemeMode) || "light";
      setThemeState(next);
      applyTheme(next);
    };
    window.addEventListener("ribif-theme-change", handler);
    return () => window.removeEventListener("ribif-theme-change", handler);
  }, []);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  return <>{children}</>;
}

