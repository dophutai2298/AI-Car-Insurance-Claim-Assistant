import type { ClaimStatus } from "../claims/types";

export type { ClaimStatus } from "../claims/types";

export type ClaimQueueItem = {
  id: string;
  claimant: string;
  vehicle: string;
  status: ClaimStatus;
  updatedAt: string;
};

export type QueueMixPoint = {
  status: ClaimStatus;
  value: number;
};

export type DashboardOverview = {
  metrics: {
    totalClaims: number;
    pendingReviews: number;
    aiApproved: number;
    aiRejected: number;
  };
  claims: ClaimQueueItem[];
  queueMix: QueueMixPoint[];
};
