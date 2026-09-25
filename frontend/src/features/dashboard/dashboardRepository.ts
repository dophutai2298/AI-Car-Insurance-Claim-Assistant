import type { DashboardOverview } from "./types";
import { listClaims } from "../claims/claimsApi";

export async function getDashboardOverview(
  accessToken: string,
): Promise<DashboardOverview> {
  const claims = await listClaims(accessToken);
  const pendingReviews = claims.filter(
    (claim) => claim.status === "REVIEW_REQUIRED",
  ).length;
  const aiApproved = claims.filter(
    (claim) => claim.status === "AI_APPROVED",
  ).length;
  const aiRejected = claims.filter(
    (claim) => claim.status === "AI_REJECTED",
  ).length;
  const sortedClaims = [...claims].sort(
    (left, right) =>
      new Date(right.updated_at).getTime() -
      new Date(left.updated_at).getTime(),
  );

  return {
    metrics: {
      totalClaims: claims.length,
      pendingReviews,
      aiApproved,
      aiRejected,
    },
    claims: sortedClaims.map((claim) => ({
      id: claim.id,
      claimant: claim.claimant_name,
      vehicle: claim.vehicle_summary,
      status: claim.status,
      updatedAt: claim.updated_at,
    })),
    queueMix: Object.entries(
      claims.reduce<Record<string, number>>((counts, claim) => {
        counts[claim.status] = (counts[claim.status] ?? 0) + 1;
        return counts;
      }, {}),
    ).map(([status, value]) => ({
      status: status as DashboardOverview["claims"][number]["status"],
      value,
    })),
  };
}
