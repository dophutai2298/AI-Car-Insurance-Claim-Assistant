import { Switch } from "@heroui/react";
import { useTranslation } from "react-i18next";

import { languageStorageKey } from "../../i18n";
import ukFlag from "../../i18n/icon/uk.png";
import vietnamFlag from "../../i18n/icon/vietnam.png";

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation();
  const isVietnamese = i18n.language.startsWith("vi");

  async function changeLanguage(selected: boolean) {
    const language = selected ? "vi" : "en";
    await i18n.changeLanguage(language);
    window.localStorage.setItem(languageStorageKey, language);
  }

  return (
    <Switch
      aria-label={t("language.label")}
      className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-white"
      isSelected={isVietnamese}
      onChange={(selected) => void changeLanguage(selected)}
      size="sm"
    >
      <Switch.Content className="flex w-full items-center justify-center gap-2">
        <img
          alt=""
          aria-hidden="true"
          className={`h-4 w-6 rounded-sm object-cover ring-1 ring-white/10 transition-opacity ${
            isVietnamese ? "opacity-45" : "opacity-100"
          }`}
          src={ukFlag}
        />
        <Switch.Control className="bg-slate-600 data-[selected=true]:bg-blue-500">
          <Switch.Thumb />
        </Switch.Control>
        <img
          alt=""
          aria-hidden="true"
          className={`h-4 w-6 rounded-sm object-cover ring-1 ring-white/10 transition-opacity ${
            isVietnamese ? "opacity-100" : "opacity-45"
          }`}
          src={vietnamFlag}
        />
      </Switch.Content>
    </Switch>
  );
}
