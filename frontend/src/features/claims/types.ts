export type ClaimStatus =
  | "DRAFT"
  | "ANALYZING"
  | "REVIEW_REQUIRED"
  | "AI_APPROVED"
  | "AI_REJECTED"
  | "FAILED";

export type EvidenceCategory =
  | "VEHICLE_DAMAGE_IMAGE"
  | "ID_CARD"
  | "INSURANCE_POLICY"
  | "VEHICLE_REGISTRATION"
  | "DRIVER_LICENSE"
  | "OTHER_DOCUMENT";

export type VehicleMetadata = {
  make: string;
  model: string;
  year: number;
  license_plate: string | null;
  vin: string | null;
};
export type IncidentInformation = {
  occurred_at: string;
  location: string;
  description: string;
};

export type ClaimDetail = {
  id: string;
  claimant_name: string;
  vehicle: VehicleMetadata;
  incident?: IncidentInformation | null;
  status: ClaimStatus;
  created_at: string;
  updated_at: string;
  evidence: EvidenceItem[];
  latest_damage_analysis: DamageAnalysis | null;
  latest_analysis_run?: WorkflowAnalysisRun | null;
  copilot_review_history?: CopilotConclusionReview[];
};

export type EvidenceItem = {
  id: number;
  category: EvidenceCategory;
  original_filename: string;
  content_type: string | null;
  file_size: number;
  uploaded_at: string;
  content_url: string;
  group_id?: number | null;
  group_label?: string | null;
  analysis_required?: boolean;
};

export type EvidenceUploadItem = { file: File; category: EvidenceCategory };
export type AnalysisRunStatus =
  "PENDING" | "PROCESSING" | "COMPLETED" | "PARTIAL" | "FAILED";
export type AnalysisResultStatus =
  "PENDING" | "PROCESSING" | "COMPLETED" | "PARTIAL" | "FAILED";

export type FieldValidationStatus =
  "VALID" | "INVALID" | "UNCERTAIN" | "MISSING" | "LLM_UNAVAILABLE";

export type ConsistencyStatus = "MATCH" | "MISMATCH" | "UNAVAILABLE";

export type DocumentFieldComparison = {
  claim_value: string | null;
  document_value: string | null;
  status: ConsistencyStatus;
  explanation: string;
};

export type DocumentFieldValidation = {
  id: number;
  analysis_run_id: number;
  document_ocr_result_id: number;
  source_evidence_id: number;
  field_key: string;
  prompt_version: string;
  ocr_value: string | null;
  normalized_value: string | null;
  status: FieldValidationStatus;
  confidence: number;
  summary: string;
  warnings: string[];
};

export type DocumentExtractedField = {
  id: number;
  analysis_run_id: number;
  extraction_result_id: number;
  source_evidence_id: number;
  field_key: string;
  ai_extracted_value: string | null;
  confirmed_value: string | null;
  prompt_version: string;
  schema_version: string;
  created_at: string;
  updated_at: string;
  comparison?: DocumentFieldComparison | null;
};

export type DocumentExtractionResult = {
  id: number;
  analysis_run_id: number;
  document_ocr_result_id: number;
  source_evidence_id: number;
  document_type: EvidenceCategory;
  status: AnalysisResultStatus;
  prompt_version: string;
  schema_version: string;
  warning: string | null;
  created_at: string;
  processed_at: string | null;
  reused?: boolean;
  fields: DocumentExtractedField[];
};

export type DocumentOcrResult = {
  id: number;
  source_evidence_id: number;
  document_type: EvidenceCategory;
  original_filename: string;
  content_type: string | null;
  status: AnalysisResultStatus;
  raw_text: string | null;
  adapter_name: string | null;
  adapter_metadata: Record<string, unknown>;
  warning: string | null;
  created_at: string;
  processed_at: string | null;
  reused?: boolean;
  extraction?: DocumentExtractionResult | null;
  field_validations: DocumentFieldValidation[];
};

export type ClaimConsistencyCheck = {
  id: number;
  field_validation_id: number;
  source_evidence_id: number;
  field_key: string;
  claim_value: string;
  document_value: string;
  status: ConsistencyStatus;
  explanation: string;
};

export type DocumentAnalysisField = {
  id: number;
  key: string;
  label: string;
  original_ai_value: string;
  reviewed_value: string;
  confidence: number;
  status: "VALID" | "WARNING";
};

export type DocumentAnalysis = {
  id: number;
  document_type: EvidenceCategory;
  status: AnalysisResultStatus;
  fields: DocumentAnalysisField[];
  warnings: string[];
};

export type WorkflowAnalysisRun = {
  id: number;
  status: AnalysisRunStatus;
  damage_status: AnalysisResultStatus;
  damage_analysis: DamageAnalysis | null;
  document_analyses: DocumentAnalysis[];
  document_ocr_results?: DocumentOcrResult[];
  consistency_checks?: ClaimConsistencyCheck[];
  failure_reason: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  inputs_changed?: boolean;
};

export type DamageAssessment =
  | "NO_DAMAGE"
  | "REPAIR_LIKELY"
  | "REPLACEMENT_LIKELY"
  | "MANUAL_INSPECTION_REQUIRED";
export type DamageDetection = {
  vehicle_part: string | null;
  damage_type: string | null;
  damage_percentage: number;
  confidence: number;
  status: "DETECTED" | "NO_SIGNIFICANT_DAMAGE";
  annotated_evidence: EvidenceItem;
};

export type DamageAnalysis = {
  id: string;
  assessment: DamageAssessment;
  warning: string | null;
  detections: DamageDetection[];
  rules: {
    confidence_threshold: number;
    repair_max_percentage: number;
    replacement_min_percentage: number;
  } | null;
  reference_price_status: ReferencePriceLookupStatus;
  reference_prices: ReferencePartPrice[];
  copilot_conclusion: CopilotConclusion | null;
  created_at: string;
};

export type ReferencePriceLookupStatus =
  "FOUND" | "UNAVAILABLE" | "NOT_REQUESTED";
export type ReferencePartPrice = {
  part_identity: string;
  amount: number | null;
  currency: string | null;
  source_name: string | null;
  source_url: string | null;
  price_type: string;
  retrieved_at: string;
  status: "FOUND" | "UNAVAILABLE";
  failure_reason: string | null;
};

export type CopilotConclusion = {
  id: number;
  status: "GENERATED" | "FALLBACK" | "LLM_UNAVAILABLE";
  recommendation: "MANUAL_ADJUSTER_REVIEW";
  summary: string;
  fallback_summary: string | null;
  failure_reason: string | null;
  provider_model: string | null;
  findings: CopilotFinding[];
  warnings: string[];
  reference_prices: ReferencePartPrice[];
  review_history: CopilotConclusionReview[];
  validity_percentage?: number | null;
  review_status?: string | null;
  evidence_references?: Array<{
    id: number;
    category: EvidenceCategory;
    original_filename: string;
  }>;
};

export type CopilotConclusionReviewStatus = "APPROVED" | "REJECTED";
export type CopilotConclusionRejectionCategory =
  | "DOCUMENT_INFORMATION_INCOMPLETE"
  | "DOCUMENT_INFORMATION_INCORRECT"
  | "DAMAGE_ASSESSMENT_ISSUE"
  | "DAMAGE_EVIDENCE_ISSUE"
  | "MISSING_EVIDENCE"
  | "INCORRECT_AI_CONCLUSION"
  | "OTHER";

export type CopilotConclusionReview = {
  claim_id: string;
  conclusion_id: number;
  status: CopilotConclusionReviewStatus;
  reason_category: CopilotConclusionRejectionCategory | null;
  comment: string | null;
  reviewer: string;
  reviewed_at: string;
  reverted_at?: string | null;
  reverted_by?: string | null;
  revert_note?: string | null;
};

export type CopilotConclusionReviewInput = {
  status: CopilotConclusionReviewStatus;
  reason_category?: CopilotConclusionRejectionCategory;
  comment: string;
};
export type CopilotFinding = {
  vehicle_part: string | null;
  damage_type: string | null;
  damage_percentage: number;
  confidence: number;
  annotated_evidence: EvidenceItem;
};
export type ClaimListItem = {
  id: string;
  claimant_name: string;
  vehicle_summary: string;
  status: ClaimStatus;
  updated_at: string;
};
export type ClaimCreateInput = {
  claimant_name: string;
  vehicle: VehicleMetadata;
  incident: IncidentInformation;
};
export type ClaimInformationInput = ClaimCreateInput;
