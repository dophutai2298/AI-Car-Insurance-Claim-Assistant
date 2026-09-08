import type {
  ClaimCreateInput,
  ClaimDetail,
  ClaimListItem,
  ClaimStatus,
  EvidenceUploadItem,
} from './types'

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

export async function uploadEvidence(
  claimId: string,
  items: EvidenceUploadItem[],
  accessToken: string,
) {
  const formData = new FormData()
  for (const item of items) {
    formData.append('files', item.file)
    formData.append('categories', item.category)
  }

  const response = await fetch(`/api/claims/${claimId}/evidence`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${accessToken}` },
    body: formData,
  })
  const body: unknown = await response.json()
  if (!response.ok) {
    const message =
      typeof body === 'object' && body !== null && 'detail' in body && typeof body.detail === 'string'
        ? body.detail
        : 'Unable to upload evidence'
    throw new ClaimsApiError(message)
  }
  return body as ClaimDetail
}

export async function getEvidenceContent(contentUrl: string, accessToken: string) {
  const response = await fetch(contentUrl, { headers: { Authorization: `Bearer ${accessToken}` } })
  if (!response.ok) throw new ClaimsApiError('Unable to load evidence preview')
  return response.blob()
}
