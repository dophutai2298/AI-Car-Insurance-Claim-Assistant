import { Translate } from "@carbon/icons-react";
import { Switch } from "@heroui/react";
import { useTranslation } from "react-i18next";

import { languageStorageKey } from "../../i18n";

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
      <Switch.Content className="flex w-full items-center gap-2">
        <Translate
          aria-hidden="true"
          className="shrink-0 text-slate-300"
          size={17}
        />
        <span
          className={
            isVietnamese ? "text-slate-400" : "font-semibold text-white"
          }
        >
          EN
        </span>
        <Switch.Control className="mx-1 bg-slate-600 data-[selected=true]:bg-blue-500">
          <Switch.Thumb />
        </Switch.Control>
        <span
          className={
            isVietnamese ? "font-semibold text-white" : "text-slate-400"
          }
        >
          VI
        </span>
        <span className="ml-auto hidden text-xs text-slate-300 lg:inline">
          {isVietnamese ? t("language.vietnamese") : t("language.english")}
        </span>
      </Switch.Content>
    </Switch>
  );
}
