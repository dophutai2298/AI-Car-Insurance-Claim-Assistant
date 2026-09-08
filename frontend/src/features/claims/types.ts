export type ClaimStatus =
  | 'DRAFT'
  | 'ANALYZING'
  | 'REVIEW_REQUIRED'
  | 'AI_APPROVED'
  | 'AI_REJECTED'
  | 'FAILED'

export type VehicleMetadata = {
  make: string
  model: string
  year: number
  license_plate: string | null
  vin: string | null
}

export type ClaimDetail = {
  id: string
  claimant_name: string
  vehicle: VehicleMetadata
  status: ClaimStatus
  created_at: string
  updated_at: string
}

export type ClaimListItem = {
  id: string
  claimant_name: string
  vehicle_summary: string
  status: ClaimStatus
  updated_at: string
}

export type ClaimCreateInput = {
  claimant_name: string
  vehicle: VehicleMetadata
}
