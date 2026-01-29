import { getCookie, setCookie } from "@/utils/cookies";

export type ThemeMode = "light" | "dark";

export const THEME_COOKIE = "ribif_theme";

export const getTheme = (): ThemeMode => {
  const raw = getCookie(THEME_COOKIE);
  return raw === "light" ? "light" : "dark";
};

export const setTheme = (mode: ThemeMode) => {
  setCookie(THEME_COOKIE, mode, 365);
};

