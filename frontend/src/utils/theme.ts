import { getCookie, setCookie } from "@/utils/cookies";

export type ThemeMode = "light" | "dark";

export const THEME_COOKIE = "ribif_theme";

export const getTheme = (): ThemeMode => {
  const raw = getCookie(THEME_COOKIE);
  return raw === "dark" ? "dark" : "light";
};

export const setTheme = (mode: ThemeMode) => {
  setCookie(THEME_COOKIE, mode, 365);
  // Dispatch custom event to notify ThemeProvider
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("ribif-theme-change", { detail: mode }));
  }
};

