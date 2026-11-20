// Theme management: auto (system) / light / dark, persisted.
// Sets data-theme="light"|"dark" on <html>; "auto" follows
// prefers-color-scheme via a media listener.
import { useEffect, useState } from "react";

const LS_KEY = "secops_theme";

function systemDark() {
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function apply(mode) {
  const resolved = mode === "auto" ? (systemDark() ? "dark" : "light") : mode;
  document.documentElement.dataset.theme = resolved;
  document.documentElement.style.colorScheme = resolved;
}

export function getTheme() {
  return localStorage.getItem(LS_KEY) || "auto";
}

export function setTheme(mode) {
  localStorage.setItem(LS_KEY, mode);
  apply(mode);
  listeners.forEach((fn) => fn(mode));
}

const listeners = new Set();

// react to system changes while in auto mode
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  if (getTheme() === "auto") apply("auto");
});

// apply once at module load (before first paint of React tree)
apply(getTheme());

export function useTheme() {
  const [theme, setThemeState] = useState(getTheme());
  useEffect(() => {
    const fn = (m) => setThemeState(m);
    listeners.add(fn);
    return () => listeners.delete(fn);
  }, []);
  return [theme, setThemeState];
}
