export type ClaimStatus =
  | 'DRAFT'
  | 'ANALYZING'
  | 'REVIEW_REQUIRED'
  | 'AI_APPROVED'
  | 'AI_REJECTED'
  | 'FAILED'

export type EvidenceCategory =
  | 'VEHICLE_DAMAGE_IMAGE'
  | 'ID_CARD'
  | 'INSURANCE_POLICY'
  | 'VEHICLE_REGISTRATION'
  | 'DRIVER_LICENSE'
  | 'OTHER_DOCUMENT'

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
  evidence: EvidenceItem[]
}

export type EvidenceItem = {
  id: number
  category: EvidenceCategory
  original_filename: string
  content_type: string | null
  file_size: number
  uploaded_at: string
  content_url: string
}

export type EvidenceUploadItem = {
  file: File
  category: EvidenceCategory
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
