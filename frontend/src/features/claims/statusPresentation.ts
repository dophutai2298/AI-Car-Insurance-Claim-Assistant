import type { ClaimStatus } from "./types";

export const statusTone: Record<
  ClaimStatus,
  "default" | "accent" | "success" | "warning" | "danger"
> = {
  DRAFT: "default",
  ANALYZING: "accent",
  REVIEW_REQUIRED: "warning",
  AI_APPROVED: "success",
  AI_REJECTED: "danger",
  FAILED: "danger",
};

export const statusLabel: Record<ClaimStatus, string> = {
  DRAFT: "Draft",
  ANALYZING: "Analyzing",
  REVIEW_REQUIRED: "Review required",
  AI_APPROVED: "AI approved",
  AI_REJECTED: "AI rejected",
  FAILED: "Failed",
};

export const lifecycleAction: Partial<
  Record<ClaimStatus, { nextStatus: ClaimStatus; label: string }>
> = {
  DRAFT: { nextStatus: "ANALYZING", label: "Begin AI analysis" },
  FAILED: { nextStatus: "ANALYZING", label: "Retry AI analysis" },
};
