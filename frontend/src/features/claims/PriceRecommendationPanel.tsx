import { CheckmarkOutline, WarningAlt } from "@carbon/icons-react";
import { Chip } from "@heroui/react";
import { useTranslation } from "react-i18next";
import type { PriceRecommendation } from "./types";

export function PriceRecommendationPanel({
  value,
  isStale = false,
}: {
  value: PriceRecommendation;
  isStale?: boolean;
}) {
  const { t } = useTranslation();
  const manual = isStale || value.recommendation === "MANUAL_REVIEW";
  const Icon = manual ? WarningAlt : CheckmarkOutline;
  return (
    <section
      aria-label={t("pricing.recommendationTitle")}
      className={`border-l-4 p-4 ${manual ? "border-amber-500 bg-amber-50" : "border-teal-600 bg-teal-50"}`}
    >
      <div className="flex flex-wrap items-center gap-3">
        <Icon
          aria-hidden="true"
          size={22}
          className={`shrink-0 ${manual ? "text-amber-800" : "text-teal-800"}`}
        />
        <h3 className="text-sm font-semibold text-slate-950">
          {t("pricing.recommendationTitle")}
        </h3>
        <Chip size="sm" variant="soft" color={manual ? "warning" : "success"}>
          {isStale
            ? t("pricing.staleRecommendation")
            : t(`pricing.recommendation.${value.recommendation}`)}
        </Chip>
      </div>
      {isStale ? (
        <p className="mt-3 text-sm font-semibold text-amber-900">
          {t("pricing.staleDescription")}
        </p>
      ) : null}
      <p className="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-slate-800">
        {value.rationale}
      </p>
      <p className="mt-2 text-xs leading-5 text-slate-600">
        {t("pricing.recommendationDisclaimer")}
      </p>
    </section>
  );
}
