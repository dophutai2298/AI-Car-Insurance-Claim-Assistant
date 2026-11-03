import { Asleep, Light } from "@carbon/icons-react";
import { Button, Tooltip } from "@heroui/react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { applyTheme, themeStorageKey, type Theme } from "../lib/theme";

export function ThemeToggle() {
  const { t } = useTranslation();
  const [theme, setTheme] = useState<Theme>(() =>
    document.documentElement.dataset.theme === "dark" ? "dark" : "light",
  );
  const label = t(theme === "dark" ? "chrome.lightTheme" : "chrome.darkTheme");
  return (
    <Tooltip>
      <Button
        aria-label={label}
        isIconOnly
        variant="ghost"
        size="sm"
        onPress={() => {
          const next = theme === "dark" ? "light" : "dark";
          applyTheme(next);
          localStorage.setItem(themeStorageKey, next);
          setTheme(next);
        }}
      >
        {theme === "dark" ? <Light size={20} /> : <Asleep size={20} />}
      </Button>
      <Tooltip.Content>{label}</Tooltip.Content>
    </Tooltip>
  );
}
