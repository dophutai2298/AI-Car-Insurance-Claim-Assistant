import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "../auth/AuthProvider";
import {
  createClaim,
  deleteEvidence,
  getClaim,
  listClaims,
  reviewCopilotConclusion,
  revertCopilotConclusionReview,
  runDamageAnalysis,
  runWorkflowAiReview,
  startWorkflowAnalysis,
  transitionClaimStatus,
  updateClaimInformation,
  updateDocumentExtractedField,
  updateDocumentExtractedFields,
  updateDocumentField,
  updateDocumentFieldValidation,
  uploadEvidence,
} from "./claimsApi";
import type {
  ClaimCreateInput,
  ClaimInformationInput,
  ClaimStatus,
  CopilotConclusionReviewInput,
  EvidenceUploadItem,
} from "./types";

export const claimsQueryKey = ["claims"] as const;

function useClaimCache() {
  const queryClient = useQueryClient();
  return (claim: { id: string }) => {
    queryClient.setQueryData([...claimsQueryKey, claim.id], claim);
    void queryClient.invalidateQueries({ queryKey: claimsQueryKey });
    void queryClient.invalidateQueries({ queryKey: ["dashboard-overview"] });
  };
}

export function useClaims() {
  const { session } = useAuth();
  return useQuery({
    queryKey: claimsQueryKey,
    queryFn: () => listClaims(session!.access_token),
    enabled: Boolean(session),
  });
}

export function useClaim(claimId: string | undefined) {
  const { session } = useAuth();
  return useQuery({
    queryKey: [...claimsQueryKey, claimId],
    queryFn: () => getClaim(claimId!, session!.access_token),
    enabled: Boolean(session && claimId),
    refetchInterval: (query) =>
      ["PENDING", "PROCESSING"].includes(
        query.state.data?.latest_analysis_run?.status ?? "",
      )
        ? 1500
        : false,
  });
}

export function useCreateClaim() {
  const { session } = useAuth();
  const cache = useClaimCache();
  return useMutation({
    mutationFn: (input: ClaimCreateInput) =>
      createClaim(input, session!.access_token),
    onSuccess: cache,
  });
}

export function useUpdateClaimInformation(claimId: string | undefined) {
  const { session } = useAuth();
  const cache = useClaimCache();
  return useMutation({
    mutationFn: (input: ClaimInformationInput) =>
      updateClaimInformation(claimId!, input, session!.access_token),
    onSuccess: cache,
  });
}

export function useTransitionClaim(claimId: string | undefined) {
  const { session } = useAuth();
  const cache = useClaimCache();
  return useMutation({
    mutationFn: (status: ClaimStatus) =>
      transitionClaimStatus(claimId!, status, session!.access_token),
    onSuccess: cache,
  });
}

export function useUploadEvidence(claimId: string | undefined) {
  const { session } = useAuth();
  const cache = useClaimCache();
  return useMutation({
    mutationFn: ({
      items,
      otherDocumentLabel,
    }: {
      items: EvidenceUploadItem[];
      otherDocumentLabel?: string;
    }) =>
      uploadEvidence(
        claimId!,
        items,
        session!.access_token,
        otherDocumentLabel,
      ),
    onSuccess: cache,
  });
}

export function useDeleteEvidence(claimId: string | undefined) {
  const { session } = useAuth();
  const cache = useClaimCache();
  return useMutation({
    mutationFn: (evidenceId: number) =>
      deleteEvidence(claimId!, evidenceId, session!.access_token),
    onSuccess: cache,
  });
}

export function useDamageAnalysis(claimId: string | undefined) {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => runDamageAnalysis(claimId!, session!.access_token),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: [...claimsQueryKey, claimId] }),
  });
}

export function useWorkflowAnalysis(claimId: string | undefined) {
  const { session } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => startWorkflowAnalysis(claimId!, session!.access_token),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: [...claimsQueryKey, claimId] }),
  });
}

export function useUpdateDocumentField(claimId: string | undefined) {
  const { session } = useAuth();
  const cache = useClaimCache();
  return useMutation({
    mutationFn: ({
      documentId,
      fieldId,
      reviewedValue,
    }: {
      documentId: number;
      fieldId: number;
      reviewedValue: string;
    }) =>
      updateDocumentField(
        claimId!,
        documentId,
        fieldId,
        reviewedValue,
        session!.access_token,
      ),
    onSuccess: cache,
  });
}

export function useUpdateDocumentFieldValidation(
  claimId: string | undefined,
  runId: number,
) {
  const { session } = useAuth();
  const cache = useClaimCache();
  return useMutation({
    mutationFn: ({
      fieldValidationId,
      reviewedValue,
    }: {
      fieldValidationId: number;
      reviewedValue: string;
    }) =>
      updateDocumentFieldValidation(
        claimId!,
        runId,
        fieldValidationId,
        reviewedValue,
        session!.access_token,
      ),
    onSuccess: cache,
  });
}

export function useUpdateDocumentExtractedField(
  claimId: string | undefined,
  runId: number,
) {
  const { session } = useAuth();
  const cache = useClaimCache();
  return useMutation({
    mutationFn: ({
      extractedFieldId,
      confirmedValue,
    }: {
      extractedFieldId: number;
      confirmedValue: string | null;
    }) =>
      updateDocumentExtractedField(
        claimId!,
        runId,
        extractedFieldId,
        confirmedValue,
        session!.access_token,
      ),
    onSuccess: cache,
  });
}

export function useUpdateDocumentExtractedFields(
  claimId: string | undefined,
  runId: number,
) {
  const { session } = useAuth();
  const cache = useClaimCache();
  return useMutation({
    mutationFn: (
      fields: Array<{ id: number; confirmed_value: string | null }>,
    ) =>
      updateDocumentExtractedFields(
        claimId!,
        runId,
        fields,
        session!.access_token,
      ),
    onSuccess: cache,
  });
}

export function useWorkflowAiReview(
  claimId: string | undefined,
  runId: number | undefined,
) {
  const { session } = useAuth();
  const cache = useClaimCache();
  return useMutation({
    mutationFn: () =>
      runWorkflowAiReview(claimId!, runId!, session!.access_token),
    onSuccess: cache,
  });
}

export function useReviewCopilotConclusion(
  claimId: string | undefined,
  conclusionId: number | undefined,
) {
  const { session } = useAuth();
  const cache = useClaimCache();
  return useMutation({
    mutationFn: (input: CopilotConclusionReviewInput) =>
      reviewCopilotConclusion(
        claimId!,
        conclusionId!,
        input,
        session!.access_token,
      ),
    onSuccess: cache,
  });
}

export function useRevertCopilotReview(
  claimId: string | undefined,
  conclusionId: number | undefined,
) {
  const { session } = useAuth();
  const cache = useClaimCache();
  return useMutation({
    mutationFn: (note: string) =>
      revertCopilotConclusionReview(
        claimId!,
        conclusionId!,
        note,
        session!.access_token,
      ),
    onSuccess: cache,
  });
}
