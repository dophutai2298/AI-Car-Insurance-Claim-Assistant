import { toast } from "@heroui/react";
import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";

import { ClaimsApiError } from "./claimsApi";
import type { WorkflowAnalysisRun } from "./types";

export function showWorkflowActionError(
  title: string,
  error: unknown,
  fallback: string,
) {
  toast.danger(title, {
    description: error instanceof ClaimsApiError ? error.message : fallback,
  });
}

export function useAnalysisCompletionToast(
  run: WorkflowAnalysisRun | null | undefined,
  acceptedRunId: number | null,
) {
  const { t } = useTranslation();
  const reportedRunId = useRef<number | null>(null);

  useEffect(() => {
    if (!run || run.id !== acceptedRunId || reportedRunId.current === run.id)
      return;
    if (!["COMPLETED", "PARTIAL", "FAILED"].includes(run.status)) return;

    reportedRunId.current = run.id;

    if (run.status === "COMPLETED") {
      toast.success(t("toast.analysisCompleted"));
    } else if (run.status === "PARTIAL") {
      toast.warning(t("toast.analysisPartial"));
    } else if (run.status === "FAILED") {
      toast.danger(t("toast.analysisFailed"), {
        description: run.failure_reason ?? t("analysis.failed"),
      });
    }
  }, [acceptedRunId, run, t]);
}
