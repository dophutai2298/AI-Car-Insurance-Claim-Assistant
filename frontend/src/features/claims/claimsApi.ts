import type { ClaimCreateInput, ClaimDetail, ClaimListItem, ClaimStatus } from './types'

export class ClaimsApiError extends Error {}

async function request<T>(path: string, accessToken: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
      ...init?.headers,
    },
  })
  const body: unknown = await response.json()
  if (!response.ok) {
    const message =
      typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string'
        ? body.detail
        : 'Unable to load claims'
    throw new ClaimsApiError(message)
  }
  return body as T
}

export function listClaims(accessToken: string) {
  return request<ClaimListItem[]>('/api/claims', accessToken)
}

export function getClaim(claimId: string, accessToken: string) {
  return request<ClaimDetail>(`/api/claims/${claimId}`, accessToken)
}

export function createClaim(input: ClaimCreateInput, accessToken: string) {
  return request<ClaimDetail>('/api/claims', accessToken, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function transitionClaimStatus(claimId: string, status: ClaimStatus, accessToken: string) {
  return request<ClaimDetail>(`/api/claims/${claimId}/status`, accessToken, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
}
