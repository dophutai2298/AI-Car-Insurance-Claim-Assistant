import { ArrowLeft, Document } from "@carbon/icons-react";
import { Alert, Chip, Skeleton } from "@heroui/react";
import { useTranslation } from "react-i18next";
import { Link, useParams } from "react-router";

import { ClaimInformationPanel } from "./ClaimInformationPanel";
import {
  ClaimWorkflowStepper,
  claimWorkflowForClaim,
  type ClaimStepId,
} from "./ClaimWorkflowStepper";
import { EvidencePanel } from "./EvidencePanel";
import {
  AiReviewPanel,
  AnalysisPanel,
  CopilotReviewHistory,
  HumanReviewPanel,
} from "./WorkflowPanels";
import { statusTone } from "./statusPresentation";
import { useClaim } from "./useClaims";

export function ClaimDetailPage() {
  const { claimId } = useParams();
  const { t } = useTranslation();
  const { data: claim, error, isPending } = useClaim(claimId);

  if (isPending)
    return (
      <div className="mx-auto grid max-w-[1440px] gap-6 py-2">
        <Skeleton className="h-10 w-40 rounded-lg" />
        <Skeleton className="h-72 rounded-lg" />
      </div>
    );
  if (error || !claim)
    return (
      <div className="mx-auto max-w-[1440px] py-2">
        <Alert status="danger">
          <Alert.Title>{t("claim.unavailable")}</Alert.Title>
          <Alert.Description>{t("claim.loadFailed")}</Alert.Description>
        </Alert>
        <Link
          className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-blue-700"
          to="/claims"
        >
          <ArrowLeft size={18} />
          {t("claim.backToClaims")}
        </Link>
      </div>
    );

  const workflow = claimWorkflowForClaim(claim);
  const analysisLocked = ["PENDING", "PROCESSING"].includes(
    claim.latest_analysis_run?.status ?? "",
  );
  const currentConclusion =
    claim.latest_analysis_run?.damage_analysis?.copilot_conclusion ??
    (!claim.latest_analysis_run
      ? claim.latest_damage_analysis?.copilot_conclusion
      : undefined);
  const reviewed = currentConclusion?.review_history[0];
  const evidenceLocked =
    analysisLocked || Boolean(reviewed && !reviewed.reverted_at);

  function navigateToStep(step: ClaimStepId) {
    document
      .getElementById(step)
      ?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <div className="mx-auto grid max-w-[1440px] gap-6 py-2">
      <Link
        className="flex w-fit items-center gap-2 text-sm font-semibold text-blue-700"
        to="/claims"
      >
        <ArrowLeft size={18} />
        {t("claim.backToClaims")}
      </Link>
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-500">
            {t("claim.case")}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">
            {t("claim.claimNumber", { id: claim.id })}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {t("claim.createdFor", { name: claim.claimant_name })}
          </p>
        </div>
        <Chip color={statusTone[claim.status]} variant="soft">
          {t(`claim.status.${claim.status}`)}
        </Chip>
      </header>
      <ClaimWorkflowStepper
        current={workflow.current}
        onNavigate={navigateToStep}
        states={workflow.states}
      />
      <ClaimInformationPanel claim={claim} />
      <EvidencePanel
        claimId={claim.id}
        evidence={claim.evidence ?? []}
        locked={evidenceLocked}
      />
      <AnalysisPanel claim={claim} />
      <AiReviewPanel claim={claim} />
      <HumanReviewPanel claim={claim} />
      <CopilotReviewHistory history={claim.copilot_review_history ?? []} />
      <Alert status="warning">
        <Document size={18} />
        <Alert.Title>{t("claim.safetyTitle")}</Alert.Title>
        <Alert.Description>{t("claim.safetyDescription")}</Alert.Description>
      </Alert>
    </div>
  );
}
