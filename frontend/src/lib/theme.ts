export const themeStorageKey = "app.theme";
export type Theme = "light" | "dark";

export function initializeTheme() {
  const stored = localStorage.getItem(themeStorageKey);
  const theme =
    stored === "light" || stored === "dark"
      ? stored
      : document.documentElement.dataset.theme === "dark" ||
          document.documentElement.classList.contains("dark") ||
          window.matchMedia?.("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light";
  applyTheme(theme);
}

export function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.classList.toggle("dark", theme === "dark");
  document.documentElement.style.colorScheme = theme;
}
