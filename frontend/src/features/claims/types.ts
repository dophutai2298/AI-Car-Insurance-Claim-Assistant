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
  latest_damage_analysis: DamageAnalysis | null
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

export type DamageAssessment =
  | 'NO_DAMAGE'
  | 'REPAIR_LIKELY'
  | 'REPLACEMENT_LIKELY'
  | 'MANUAL_INSPECTION_REQUIRED'

export type DamageDetection = {
  vehicle_part: string | null
  damage_type: string | null
  damage_percentage: number
  confidence: number
  status: 'DETECTED' | 'NO_SIGNIFICANT_DAMAGE'
  annotated_evidence: EvidenceItem
}

export type DamageAnalysis = {
  id: string
  assessment: DamageAssessment
  warning: string | null
  detections: DamageDetection[]
  created_at: string
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
