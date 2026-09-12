import type { ClaimStatus } from "../claims/types";

export type { ClaimStatus } from "../claims/types";

export type CapabilityState = "ready" | "mock" | "warning";

export type ClaimQueueItem = {
  id: string;
  claimant: string;
  vehicle: string;
  status: ClaimStatus;
  evidenceCount: number;
  assessment:
    | "Not assessed"
    | "Repair likely"
    | "Replacement likely"
    | "Manual inspection";
  updatedAt: string;
};

export type QueueMixPoint = {
  name: string;
  value: number;
};

export type RuntimeCapability = {
  name: string;
  mode: string;
  state: CapabilityState;
};

export type DashboardOverview = {
  metrics: {
    openClaims: number;
    reviewRequired: number;
    avgModelLatency: string;
    aiConclusionReady: number;
  };
  claims: ClaimQueueItem[];
  queueMix: QueueMixPoint[];
  capabilities: RuntimeCapability[];
};
