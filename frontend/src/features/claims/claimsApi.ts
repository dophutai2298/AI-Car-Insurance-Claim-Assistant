import type {
  ClaimCreateInput,
  AnalysisBlockedReason,
  ClaimDetail,
  ClaimInformationInput,
  ClaimListItem,
  ClaimStatus,
  CopilotConclusionReviewInput,
  DamageAnalysis,
  EvidenceUploadItem,
  WorkflowAnalysisRun,
} from "./types";

export class ClaimsApiError extends Error {
  blockedReasons: AnalysisBlockedReason[];

  constructor(message: string, blockedReasons: AnalysisBlockedReason[] = []) {
    super(message);
    this.blockedReasons = blockedReasons;
  }
}

async function request<T>(
  path: string,
  accessToken: string,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  const body: unknown = await response.json();
  if (!response.ok) {
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? body.detail
        : null;
    const message =
      typeof detail === "string"
        ? detail
        : typeof detail === "object" &&
            detail !== null &&
            "message" in detail &&
            typeof detail.message === "string"
          ? detail.message
          : "Unable to load claims";
    const blockedReasons =
      typeof detail === "object" &&
      detail !== null &&
      "blocked_reasons" in detail &&
      Array.isArray(detail.blocked_reasons)
        ? (detail.blocked_reasons as AnalysisBlockedReason[])
        : [];
    throw new ClaimsApiError(message, blockedReasons);
  }
  return body as T;
}

export const listClaims = (accessToken: string) =>
  request<ClaimListItem[]>("/api/claims", accessToken);
export const getClaim = (claimId: string, accessToken: string) =>
  request<ClaimDetail>(`/api/claims/${claimId}`, accessToken);
export const createClaim = (input: ClaimCreateInput, accessToken: string) =>
  request<ClaimDetail>("/api/claims", accessToken, {
    method: "POST",
    body: JSON.stringify(input),
  });
export const updateClaimInformation = (
  claimId: string,
  input: ClaimInformationInput,
  accessToken: string,
) =>
  request<ClaimDetail>(`/api/claims/${claimId}/information`, accessToken, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
export const transitionClaimStatus = (
  claimId: string,
  status: ClaimStatus,
  accessToken: string,
) =>
  request<ClaimDetail>(`/api/claims/${claimId}/status`, accessToken, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
export const runDamageAnalysis = (claimId: string, accessToken: string) =>
  request<DamageAnalysis>(
    `/api/claims/${claimId}/damage-analysis`,
    accessToken,
    { method: "POST" },
  );
export const startWorkflowAnalysis = (claimId: string, accessToken: string) =>
  request<WorkflowAnalysisRun>(
    `/api/claims/${claimId}/analysis-runs`,
    accessToken,
    { method: "POST" },
  );
export const updateDocumentField = (
  claimId: string,
  documentId: number,
  fieldId: number,
  reviewedValue: string,
  accessToken: string,
) =>
  request<ClaimDetail>(
    `/api/claims/${claimId}/document-analyses/${documentId}/fields/${fieldId}`,
    accessToken,
    {
      method: "PATCH",
      body: JSON.stringify({ reviewed_value: reviewedValue }),
    },
  );
export const updateDocumentFieldValidation = (
  claimId: string,
  runId: number,
  fieldValidationId: number,
  reviewedValue: string,
  accessToken: string,
) =>
  request<ClaimDetail>(
    `/api/claims/${claimId}/analysis-runs/${runId}/field-validations/${fieldValidationId}`,
    accessToken,
    {
      method: "PATCH",
      body: JSON.stringify({ reviewed_value: reviewedValue }),
    },
  );
export const updateDocumentExtractedField = (
  claimId: string,
  runId: number,
  extractedFieldId: number,
  confirmedValue: string | null,
  accessToken: string,
) =>
  request<ClaimDetail>(
    `/api/claims/${claimId}/analysis-runs/${runId}/extraction-fields/${extractedFieldId}`,
    accessToken,
    {
      method: "PATCH",
      body: JSON.stringify({ confirmed_value: confirmedValue }),
    },
  );
export const updateDocumentExtractedFields = (
  claimId: string,
  runId: number,
  fields: Array<{ id: number; confirmed_value: string | null }>,
  accessToken: string,
) =>
  request<ClaimDetail>(
    `/api/claims/${claimId}/analysis-runs/${runId}/extraction-fields`,
    accessToken,
    {
      method: "PUT",
      body: JSON.stringify({ fields }),
    },
  );
export const runWorkflowAiReview = (
  claimId: string,
  runId: number,
  accessToken: string,
) =>
  request<ClaimDetail>(
    `/api/claims/${claimId}/analysis-runs/${runId}/ai-review`,
    accessToken,
    { method: "POST" },
  );
export const reviewCopilotConclusion = (
  claimId: string,
  conclusionId: number,
  input: CopilotConclusionReviewInput,
  accessToken: string,
) =>
  request<ClaimDetail>(
    `/api/claims/${claimId}/copilot-conclusions/${conclusionId}/review`,
    accessToken,
    { method: "POST", body: JSON.stringify(input) },
  );
export const revertCopilotConclusionReview = (
  claimId: string,
  conclusionId: number,
  note: string,
  accessToken: string,
) =>
  request<ClaimDetail>(
    `/api/claims/${claimId}/copilot-conclusions/${conclusionId}/review/revert`,
    accessToken,
    { method: "POST", body: JSON.stringify({ note }) },
  );
export const deleteEvidence = (
  claimId: string,
  evidenceId: number,
  accessToken: string,
) =>
  request<ClaimDetail>(
    `/api/claims/${claimId}/evidence/${evidenceId}`,
    accessToken,
    { method: "DELETE" },
  );

export async function uploadEvidence(
  claimId: string,
  items: EvidenceUploadItem[],
  accessToken: string,
  otherDocumentLabel?: string,
) {
  const formData = new FormData();
  for (const item of items) {
    formData.append("files", item.file);
    formData.append("categories", item.category);
  }
  if (otherDocumentLabel)
    formData.append("other_document_label", otherDocumentLabel);
  const response = await fetch(`/api/claims/${claimId}/evidence`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: formData,
  });
  const body: unknown = await response.json();
  if (!response.ok) {
    const message =
      typeof body === "object" &&
      body !== null &&
      "detail" in body &&
      typeof body.detail === "string"
        ? body.detail
        : "Unable to upload evidence";
    throw new ClaimsApiError(message);
  }
  return body as ClaimDetail;
}

export async function getEvidenceContent(
  contentUrl: string,
  accessToken: string,
) {
  const response = await fetch(contentUrl, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) throw new ClaimsApiError("Unable to load evidence preview");
  return response.blob();
}
