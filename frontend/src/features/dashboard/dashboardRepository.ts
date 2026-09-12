import type { DashboardOverview } from "./types";
import { listClaims } from "../claims/claimsApi";

export async function getDashboardOverview(
  accessToken: string,
): Promise<DashboardOverview> {
  const claims = await listClaims(accessToken);
  const reviewRequired = claims.filter(
    (claim) => claim.status === "REVIEW_REQUIRED",
  ).length;
  const aiConclusionReady = claims.filter((claim) =>
    ["AI_APPROVED", "AI_REJECTED"].includes(claim.status),
  ).length;

  return {
    metrics: {
      openClaims: claims.length,
      reviewRequired,
      avgModelLatency: "Not available",
      aiConclusionReady,
    },
    claims: claims.map((claim) => ({
      id: claim.id,
      claimant: claim.claimant_name,
      vehicle: claim.vehicle_summary,
      status: claim.status,
      evidenceCount: 0,
      assessment: "Not assessed",
      updatedAt: new Date(claim.updated_at).toLocaleString(),
    })),
    queueMix: Object.entries(
      claims.reduce<Record<string, number>>((counts, claim) => {
        counts[claim.status] = (counts[claim.status] ?? 0) + 1;
        return counts;
      }, {}),
    ).map(([name, value]) => ({ name: name.replaceAll("_", " "), value })),
    capabilities: [
      { name: "Damage model adapter", mode: "Not started", state: "warning" },
      { name: "Postgres", mode: "Persistent claims", state: "ready" },
      { name: "Part search", mode: "Not started", state: "warning" },
      { name: "LLM", mode: "Not started", state: "warning" },
    ],
  };
}
