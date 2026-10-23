import { useTranslation } from "react-i18next";
import type {
  AnalysisPricing,
  DamageAssessment,
  DamageDetection,
  ReferencePartPrice,
} from "./types";

export function PricingOverview({
  pricing,
  assessment,
  findings = [],
}: {
  pricing: AnalysisPricing;
  assessment: DamageAssessment;
  findings?: DamageDetection[];
}) {
  const { t, i18n } = useTranslation();
  const money = (value: number) =>
    new Intl.NumberFormat(i18n.language, {
      style: "currency",
      currency: "VND",
      maximumFractionDigits: 0,
    }).format(value);
  function priceCell(price: ReferencePartPrice) {
    if (price.status !== "FOUND" || price.amount === null) {
      return (
        <span className="text-amber-800">
          {t(
            price.unavailable_reason === "PROVIDER_UNAVAILABLE"
              ? "pricing.lookupFailed"
              : "pricing.missing",
          )}
        </span>
      );
    }
    return (
      <div className="grid gap-1">
        <span className="font-semibold tabular-nums text-slate-950">
          {money(price.amount)}
        </span>
        <span className="text-xs text-slate-500">{price.source_name}</span>
        <span className="text-xs text-slate-500">
          {price.vehicle_make} {price.vehicle_model} · {price.vehicle_year}
        </span>
        {price.effective_at ? (
          <span className="text-xs text-slate-500">
            {t("pricing.effective")}:{" "}
            {new Date(price.effective_at).toLocaleDateString(i18n.language)}
          </span>
        ) : null}
        <span className="text-xs text-slate-500">
          {t("pricing.retrieved")}:{" "}
          {new Date(price.retrieved_at).toLocaleDateString(i18n.language)}
        </span>
        {price.source_url && /^https?:\/\//i.test(price.source_url) ? (
          <a
            className="text-xs text-blue-700 underline"
            href={price.source_url}
            target="_blank"
            rel="noreferrer"
          >
            {t("pricing.source")}
          </a>
        ) : null}
      </div>
    );
  }
  return (
    <section
      aria-label={t("pricing.title")}
      className="grid min-w-0 gap-4 border-b border-slate-200 pb-6"
    >
      <div>
        <h3 className="text-base font-semibold text-slate-950">
          {t("pricing.title")}
        </h3>
        <p className="mt-1 text-sm text-slate-600">{t("pricing.mockNotice")}</p>
      </div>
      <div className="flex flex-wrap gap-x-3 gap-y-1 border-y border-slate-200 py-3 text-sm">
        <span className="font-semibold text-slate-950">
          {t("pricing.assessment")}: {t(`analysis.assessment.${assessment}`)}
        </span>
        <span className="text-slate-500">{t("pricing.independent")}</span>
      </div>
      <div className="grid gap-3 md:grid-cols-2">
        {(["repair_estimate", "replacement_part_price"] as const).map((key) => {
          const estimate = pricing[key];
          return (
            <div
              key={key}
              className={`min-w-0 rounded-lg border p-4 ${estimate.status === "COMPLETE" ? "border-teal-200 bg-teal-50/50" : "border-amber-200 bg-amber-50/50"}`}
            >
              <h4 className="text-sm font-semibold text-slate-700">
                {t(`pricing.${key}`)}
              </h4>
              <p className="mt-2 break-words text-2xl font-semibold tabular-nums text-slate-950">
                {estimate.status === "UNAVAILABLE"
                  ? t("pricing.unavailable")
                  : money(estimate.total_amount ?? estimate.known_subtotal)}
              </p>
              <p className="mt-2 text-sm text-slate-600">
                {t(`pricing.${estimate.status}`)} · {estimate.priced_parts}/
                {estimate.total_parts} {t("pricing.parts")}
              </p>
            </div>
          );
        })}
      </div>
      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table
          className="w-full min-w-[600px] border-collapse text-left text-sm"
          aria-label={t("pricing.breakdown")}
        >
          <thead className="bg-slate-50 text-xs text-slate-600">
            <tr>
              <th scope="col" className="px-4 py-3">
                {t("analysis.part")}
              </th>
              <th scope="col" className="px-4 py-3">
                {t("pricing.repair_estimate")}
              </th>
              <th scope="col" className="px-4 py-3">
                {t("pricing.replacement_part_price")}
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {pricing.line_items.map((part) => (
              <tr key={part.part_identity}>
                <th
                  scope="row"
                  className="px-4 py-4 align-top font-semibold text-slate-950"
                >
                  {part.part_identity.replaceAll("_", " ")}
                  {findings
                    .filter(
                      (item) =>
                        item.vehicle_part
                          ?.trim()
                          .toLowerCase()
                          .replaceAll("-", "_")
                          .replaceAll(" ", "_") === part.part_identity,
                    )
                    .map((item, index) => (
                      <p
                        key={index}
                        className="mt-1 text-xs font-normal text-slate-500"
                      >
                        {item.damage_type} · {item.damage_percentage}%
                      </p>
                    ))}
                </th>
                <td className="px-4 py-4 align-top">
                  {priceCell(part.repair_estimate)}
                </td>
                <td className="px-4 py-4 align-top">
                  {priceCell(part.replacement_part_price)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-slate-500">{t("pricing.humanDecision")}</p>
    </section>
  );
}
