import { CheckmarkOutline, WarningAlt } from "@carbon/icons-react";
import { useTranslation } from "react-i18next";

import { requiredEvidenceCategories } from "./EvidencePanel";
import type { ClaimDetail, ClaimStatus } from "./types";

export type ClaimStepState =
  "completed" | "current" | "available" | "blocked" | "warning" | "error";
export type ClaimStepId =
  "information" | "evidence" | "analysis" | "aiReview" | "humanReview";

const styles: Record<ClaimStepState, string> = {
  completed: "border-emerald-200 bg-emerald-50 text-emerald-800",
  current: "border-blue-300 bg-blue-50 text-blue-800",
  available: "border-slate-300 bg-white text-slate-700",
  blocked: "border-slate-200 bg-slate-50 text-slate-400",
  warning: "border-amber-300 bg-amber-50 text-amber-800",
  error: "border-red-300 bg-red-50 text-red-800",
};

export function ClaimWorkflowStepper({
  current = "information",
  states,
  onNavigate,
}: {
  current?: ClaimStepId;
  states?: Partial<Record<ClaimStepId, ClaimStepState>>;
  onNavigate?: (step: ClaimStepId) => void;
}) {
  const { t } = useTranslation();
  const steps = [
    { id: "information", label: t("claim.information") },
    { id: "evidence", label: t("claim.stepEvidence") },
    { id: "analysis", label: t("claim.stepAnalysis") },
    { id: "aiReview", label: t("claim.stepAiReview") },
    { id: "humanReview", label: t("claim.stepHumanReview") },
  ] as const;
  const currentIndex = steps.findIndex((step) => step.id === current);
  return (
    <ol aria-label={t("claim.workflow")} className="grid gap-2 md:grid-cols-5">
      {steps.map((step, index) => {
        const state =
          states?.[step.id] ??
          (index < currentIndex
            ? "completed"
            : index === currentIndex
              ? "current"
              : "blocked");
        const content = (
          <>
            <span className="flex size-7 shrink-0 items-center justify-center border border-current text-xs font-semibold">
              {state === "completed" ? (
                <CheckmarkOutline size={16} />
              ) : ["warning", "error"].includes(state) ? (
                <WarningAlt size={16} />
              ) : (
                index + 1
              )}
            </span>
            <span className="min-w-0 text-left">
              <span className="block text-sm font-semibold">{step.label}</span>
              <span className="block text-xs opacity-80">
                {t(`claim.${state}`)}
              </span>
            </span>
          </>
        );
        return (
          <li key={step.id} className="flex w-full rounded-lg shadow-sm !cursor-pointer pointer-events-auto">
            {state === "blocked" || !onNavigate ? (
              <div
                className={`flex min-h-16 w-full items-center gap-3 border px-3 py-2 ${styles[state]}`}
              >
                {content}
              </div>
            ) : (
              <button
                className={`flex min-h-16 w-full items-center gap-3 border px-3 py-2 ${styles[state]} hover:border-current`}
                onClick={() => onNavigate(step.id)}
                type="button"
              >
                {content}
              </button>
            )}
          </li>
        );
      })}
    </ol>
  );
}

export function claimWorkflowForClaim(claim: ClaimDetail) {
  const informationComplete = Boolean(claim.incident);
  const evidenceComplete = requiredEvidenceCategories.every((category) =>
    (claim.evidence ?? []).some((item) => item.category === category),
  );
  const run = claim.latest_analysis_run;
  const conclusion =
    run?.damage_analysis?.copilot_conclusion ??
    (!run ? claim.latest_damage_analysis?.copilot_conclusion : undefined);
  const latestReview = conclusion?.review_history[0];

  if (!informationComplete)
    return {
      current: "information" as const,
      states: { information: "current" as const },
    };
  if (!evidenceComplete)
    return {
      current: "evidence" as const,
      states: {
        information: "completed" as const,
        evidence: "current" as const,
      },
    };
  if (!run)
    return {
      current: "analysis" as const,
      states: {
        information: "completed" as const,
        evidence: "completed" as const,
        analysis: "current" as const,
      },
    };
  if (run.status === "PENDING" || run.status === "PROCESSING")
    return {
      current: "analysis" as const,
      states: {
        information: "available" as const,
        evidence: "available" as const,
        analysis: "current" as const,
      },
    };
  if (run.status === "FAILED")
    return {
      current: "analysis" as const,
      states: {
        information: "available" as const,
        evidence: "available" as const,
        analysis: "error" as const,
      },
    };
  if (run.inputs_changed)
    return {
      current: "analysis" as const,
      states: {
        information: "available" as const,
        evidence: "available" as const,
        analysis: "warning" as const,
        aiReview: "blocked" as const,
      },
    };
  if (!conclusion)
    return {
      current: "aiReview" as const,
      states: {
        information: "available" as const,
        evidence: "available" as const,
        analysis:
          run.status === "PARTIAL"
            ? ("warning" as const)
            : ("completed" as const),
        aiReview: "current" as const,
      },
    };
  if (latestReview?.reverted_at)
    return {
      current: "analysis" as const,
      states: {
        information: "available" as const,
        evidence: "available" as const,
        analysis: "current" as const,
        aiReview: "warning" as const,
        humanReview: "warning" as const,
      },
    };
  if (!latestReview)
    return {
      current: "humanReview" as const,
      states: {
        information: "available" as const,
        evidence: "available" as const,
        analysis:
          run.status === "PARTIAL"
            ? ("warning" as const)
            : ("completed" as const),
        aiReview: "completed" as const,
        humanReview: "current" as const,
      },
    };
  return {
    current: "humanReview" as const,
    states: {
      information: "available" as const,
      evidence: "available" as const,
      analysis: "completed" as const,
      aiReview: "completed" as const,
      humanReview: "completed" as const,
    },
  };
}

export function claimWorkflowForStatus(status: ClaimStatus) {
  if (status === "DRAFT")
    return {
      current: "evidence" as const,
      states: {
        information: "completed" as const,
        evidence: "current" as const,
      },
    };
  if (status === "ANALYZING")
    return {
      current: "analysis" as const,
      states: {
        information: "completed" as const,
        evidence: "completed" as const,
        analysis: "current" as const,
      },
    };
  if (status === "FAILED")
    return {
      current: "analysis" as const,
      states: {
        information: "completed" as const,
        evidence: "completed" as const,
        analysis: "error" as const,
      },
    };
  return {
    current: "humanReview" as const,
    states: {
      information: "completed" as const,
      evidence: "completed" as const,
      analysis: "completed" as const,
      aiReview: "completed" as const,
      humanReview:
        status === "REVIEW_REQUIRED"
          ? ("current" as const)
          : ("completed" as const),
    },
  };
}
