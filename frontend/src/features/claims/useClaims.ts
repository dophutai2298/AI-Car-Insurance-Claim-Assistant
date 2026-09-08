import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { useAuth } from '../auth/AuthProvider'
import { createClaim, getClaim, listClaims, transitionClaimStatus, uploadEvidence } from './claimsApi'
import type { ClaimCreateInput, ClaimStatus, EvidenceUploadItem } from './types'

export const claimsQueryKey = ['claims'] as const

export function useClaims() {
  const { session } = useAuth()

  return useQuery({
    queryKey: claimsQueryKey,
    queryFn: () => listClaims(session!.access_token),
    enabled: Boolean(session),
  })
}

export function useClaim(claimId: string | undefined) {
  const { session } = useAuth()

  return useQuery({
    queryKey: [...claimsQueryKey, claimId],
    queryFn: () => getClaim(claimId!, session!.access_token),
    enabled: Boolean(session && claimId),
  })
}

export function useCreateClaim() {
  const { session } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (input: ClaimCreateInput) => createClaim(input, session!.access_token),
    onSuccess: async (claim) => {
      queryClient.setQueryData([...claimsQueryKey, claim.id], claim)
      await queryClient.invalidateQueries({ queryKey: claimsQueryKey })
      await queryClient.invalidateQueries({ queryKey: ['dashboard-overview'] })
    },
  })
}

export function useTransitionClaim(claimId: string | undefined) {
  const { session } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (status: ClaimStatus) => transitionClaimStatus(claimId!, status, session!.access_token),
    onSuccess: async (claim) => {
      queryClient.setQueryData([...claimsQueryKey, claim.id], claim)
      await queryClient.invalidateQueries({ queryKey: claimsQueryKey })
      await queryClient.invalidateQueries({ queryKey: ['dashboard-overview'] })
    },
  })
}

export function useUploadEvidence(claimId: string | undefined) {
  const { session } = useAuth()
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (items: EvidenceUploadItem[]) => uploadEvidence(claimId!, items, session!.access_token),
    onSuccess: async (claim) => {
      queryClient.setQueryData([...claimsQueryKey, claim.id], claim)
      await queryClient.invalidateQueries({ queryKey: claimsQueryKey })
    },
  })
}
