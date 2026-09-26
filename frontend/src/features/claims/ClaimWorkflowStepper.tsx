import { useTranslation } from "react-i18next";

import { requiredEvidenceCategories } from "./EvidencePanel";
import type { ClaimDetail, ClaimStatus } from "./types";

export type ClaimStepState =
  "completed" | "current" | "available" | "blocked" | "warning" | "error";
export type ClaimStepId =
  "information" | "evidence" | "analysis" | "aiReview" | "humanReview";

const styles: Record<
  ClaimStepState,
  { indicator: string; state: string; surface: string }
> = {
  completed: {
    indicator: "border-blue-600 bg-blue-600 text-white",
    state: "text-blue-700",
    surface: "bg-blue-50 text-slate-950",
  },
  current: {
    indicator: "border-blue-600 bg-blue-600 text-white",
    state: "text-blue-700",
    surface: "bg-blue-50 text-slate-950",
  },
  available: {
    indicator: "border-blue-200 bg-blue-100 text-blue-800",
    state: "text-blue-700",
    surface: "bg-blue-50 text-slate-950 hover:bg-blue-100/70",
  },
  blocked: {
    indicator: "border-slate-200 bg-slate-100 text-slate-400",
    state: "text-slate-400",
    surface: "bg-slate-50 text-slate-500",
  },
  warning: {
    indicator: "border-amber-500 bg-amber-100 text-amber-800",
    state: "text-amber-800",
    surface: "bg-blue-50 text-slate-950 hover:bg-blue-100/70",
  },
  error: {
    indicator: "border-red-600 bg-red-100 text-red-800",
    state: "text-red-700",
    surface: "bg-blue-50 text-slate-950 hover:bg-blue-100/70",
  },
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
  const progressWidths = ["w-1/5", "w-2/5", "w-3/5", "w-4/5", "w-full"];

  return (
    <section className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
      <header className="flex items-center justify-between gap-4 border-b border-slate-100 px-4 py-3 sm:px-5">
        <h2 className="text-sm font-semibold text-slate-950">
          {t("claim.workflow")}
        </h2>
        <span className="font-mono text-xs font-semibold tabular-nums text-slate-500">
          {currentIndex + 1} / {steps.length}
        </span>
      </header>
      <div aria-hidden="true" className="h-1 bg-slate-100">
        <div
          className={`h-full bg-blue-600 transition-[width] duration-200 ${progressWidths[currentIndex]}`}
        />
      </div>
      <ol
        aria-label={t("claim.workflow")}
        className="grid divide-y divide-slate-100 sm:grid-cols-5 sm:divide-x sm:divide-y-0"
      >
        {steps.map((step, index) => {
          const state =
            states?.[step.id] ??
            (index < currentIndex
              ? "completed"
              : index === currentIndex
                ? "current"
                : "blocked");
          const style = styles[state];
          const content = (
            <>
              <span
                className={`flex size-8 shrink-0 items-center justify-center rounded-md border text-xs font-semibold ${style.indicator}`}
              >
                {index + 1}
              </span>
              <span className="min-w-0 text-left">
                <span className="block text-sm font-semibold leading-5">
                  {step.label}
                </span>
                <span
                  className={`mt-1 block text-xs font-medium leading-4 ${style.state}`}
                >
                  {t(`claim.${state}`)}
                </span>
              </span>
            </>
          );

          return (
            <li className="min-w-0" key={step.id}>
              {state === "blocked" || !onNavigate ? (
                <div
                  aria-current={state === "current" ? "step" : undefined}
                  className={`flex min-h-24 w-full items-start justify-start gap-3 px-4 py-4 text-left sm:px-4 ${style.surface}`}
                >
                  {content}
                </div>
              ) : (
                <button
                  aria-current={state === "current" ? "step" : undefined}
                  className={`flex min-h-24 w-full items-start justify-start gap-3 px-4 py-4 text-left transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-600 sm:px-4 ${style.surface}`}
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
    </section>
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
