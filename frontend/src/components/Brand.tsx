import { CarFront } from "@carbon/icons-react";
import { useTranslation } from "react-i18next";

export function Brand() {
  const { t } = useTranslation();
  return (
    <div className="brand">
      <span className="brand__mark">
        <CarFront size={24} aria-hidden="true" />
      </span>
      <span className="brand__copy">
        <strong>Claim Assistant</strong>
        <span>{t("chrome.insuranceWorkspace")}</span>
      </span>
    </div>
  );
}
