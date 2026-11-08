import i18n from "i18next";
import { initReactI18next } from "react-i18next";

const languageStorageKey = "app.language";
const initialLanguage =
  typeof window !== "undefined"
    ? window.localStorage.getItem(languageStorageKey)
    : null;

const en = {
  chrome: {
    insuranceWorkspace: "Insurance workspace",
    workspace: "Workspace",
    skipToContent: "Skip to content",
    openNavigation: "Open navigation",
    closeNavigation: "Close navigation",
    lightTheme: "Switch to light theme",
    darkTheme: "Switch to dark theme",
    roles: {
      ADMIN: "Administrator",
      ADJUSTER: "Claims adjuster",
      USER: "Customer",
    },
  },
  pricing: {
    staleRecommendation: "Earlier snapshot",
    staleDescription:
      "This advice is no longer current. Complete and save the updated Analysis, then rerun AI Review.",
    recommendationTitle: "AI price recommendation",
    recommendationDisclaimer:
      "Informational advice based on mock reference prices. The damage assessment remains unchanged; the adjuster makes the final decision.",
    recommendation: {
      SUPPORTS_REPAIR: "Supports repair",
      SUPPORTS_REPLACEMENT: "Supports replacement",
      MANUAL_REVIEW: "Manual pricing review required",
    },
    lookupFailed: "Price lookup unavailable. Try again later.",
    title: "Repair and replacement estimates",
    mockNotice:
      "Mock Vietnam price catalog · VND. Informational estimates, not a workshop quote or payout.",
    assessment: "Damage assessment",
    independent: "Based on confirmed damage; independent of pricing",
    repair_estimate: "Repair estimate",
    replacement_part_price: "Replacement part prices",
    COMPLETE: "Complete estimate",
    INCOMPLETE: "Known subtotal only; incomplete estimate",
    UNAVAILABLE: "No matching prices",
    unavailable: "Unavailable",
    missing: "No exact price match",
    parts: "parts priced",
    source: "Price source",
    effective: "Effective",
    retrieved: "Retrieved",
    breakdown: "Per-part price comparison",
    humanDecision:
      "Prices are reference estimates. The adjuster makes the final decision.",
  },
  myClaims: {
    eyebrow: "Customer intake",
    title: "My Claims",
    description: "Track your claims and continue any draft before submission.",
    newClaim: "New claim",
    claim: "Claim",
    created: "Created",
    status: "Status",
    action: "Action",
    continue: "Continue draft",
    submitted: "Tracking status",
    empty: "You have no claims yet.",
    loadFailed: "Your claims could not be loaded.",
    evidenceCount: "{{count}} of {{total}} required evidence types uploaded",
    submit: "Submit claim",
    submitSuccess: "Claim submitted",
    submitFailed: "Claim could not be submitted",
  },
  customerAccount: {
    eyebrow: "Customer management",
    pageTitle: "Customer Accounts",
    pageDescription:
      "Create sign-in accounts for customers so they can prepare and submit their own claims.",
    userAccounts: "Customer accounts",
    userAccountsDescription: "Create a sign-in account for a claim customer.",
    createAccount: "Create customer account",
    userFullName: "Full name",
    createUser: "Create User account",
    userCreated: "User account created",
    userCreateFailed: "User account could not be created",
    listTitle: "Customer account list",
    listDescription: "Accounts that can create and track their own claims.",
    status: "Status",
    active: "Active",
    inactive: "Inactive",
    empty: "No customer accounts have been created yet.",
    loadFailed: "Customer accounts could not be loaded",
  },
  common: {
    backToTop: "Back to top",
    edit: "Edit",
    save: "Save",
    cancel: "Cancel",
    tryAgain: "Try again.",
    notProvided: "Not provided",
    clearFilters: "Clear filters",
    sortAscending: "Sort {{column}} ascending",
    sortDescending: "Sort {{column}} descending",
  },
  toast: {
    claimInformationSaved: "Claim information saved",
    claimInformationSaveFailed: "Claim information was not saved",
    evidenceUploaded: "{{count}} evidence file(s) uploaded",
    evidenceUploadFailed: "Evidence upload was not completed",
    evidenceDeleted: "Evidence deleted",
    evidenceDeleteFailed: "Evidence was not deleted",
    analysisStarted: "Analysis started",
    analysisStartedDescription:
      "Processing continues in the background. You can leave this page.",
    analysisStartFailed: "Analysis was not started",
    analysisCompleted: "Analysis completed",
    analysisPartial: "Analysis completed with items to review",
    analysisFailed: "Analysis failed",
    documentFieldsSaved: "Document fields saved",
    documentFieldsSaveFailed: "Document fields were not saved",
    documentFieldSaved: "{{field}} saved",
    documentFieldSaveFailed: "{{field}} was not saved",
    aiReviewGenerated: "AI review generated",
    aiReviewFailed: "AI review was not generated",
    humanReviewApproved: "AI review approved",
    humanReviewRejected: "AI review rejected",
    humanReviewFailed: "Human review was not saved",
    humanReviewReverted: "Human review reverted",
    humanReviewRevertFailed: "Human review was not reverted",
    claimDeleted: "Claim deleted",
    claimDeleteFailed: "Claim was not deleted",
    claimCreated: "Claim created",
    claimCreateFailed: "Claim was not created",
  },
  navigation: {
    primary: "Primary navigation",
    dashboard: "Dashboard",
    claims: "Claims",
    customerAccounts: "Customer Accounts",
    admin: "Admin Config",
    signOut: "Sign out",
  },
  language: {
    label: "Language",
    english: "English",
    vietnamese: "Vietnamese",
    switchToVietnamese: "Tiếng Việt",
    switchToEnglish: "English",
  },
  dashboard: {
    eyebrow: "Claims operations",
    title: "Claim review workspace",
    description:
      "Monitor incoming claim files, focus the review queue, and open the evidence record that needs attention.",
    newClaim: "New claim",
    totalClaims: "Total claims",
    pendingReviews: "Pending reviews",
    aiApproved: "AI review approved",
    aiRejected: "AI review rejected",
    statusOverview: "Claim status overview",
    statusOverviewDescription:
      "Current volume by workflow status. AI outcomes are not final insurer decisions.",
    loadError: "Dashboard data could not be loaded.",
    noActivity: "No claim activity yet",
    noActivityDescription: "Status counts will appear once a claim is created.",
    needsReview: "Needs review",
    needsReviewDescription: "Cases waiting for an adjuster decision.",
    noReviewQueue: "No claims currently require adjuster review.",
    recentClaims: "Recent claims",
    recentDescription:
      "Latest activity first. Search by case details, then narrow the queue by status or update date.",
    noClaims: "No claims yet",
    noClaimsDescription: "Create a claim to begin evidence intake.",
  },
  claimsList: {
    eyebrow: "Claims",
    title: "Claim cases",
    description: "Review active intake cases and open their evidence records.",
    allClaims: "All claims",
    allClaimsDescription: "Current cases ordered by their latest update.",
    loadError: "Claim cases could not be loaded.",
  },
  queue: {
    loadFailed: "Unable to load queue",
    claim: "Claim",
    vehicle: "Vehicle",
    reviewStatus: "Review status",
    lastUpdated: "Last updated",
    empty: "No claims match the selected filters.",
    clearFilters: "Clear filters",
    claimShown: "claim shown",
    claimsShown: "claims shown",
    searchLabel: "Search claims",
    searchPlaceholder: "Claim number, claimant, or vehicle",
    status: "Status",
    allStatuses: "All statuses",
    updated: "Updated",
    allDates: "All dates",
    today: "Today",
    last7Days: "Last 7 days",
    last30Days: "Last 30 days",
    showing: "Showing {{first}}-{{last}} of {{total}} claims",
    none: "No claims to show",
    rowsPerPage: "Rows per page",
    page: "Page {{current}} of {{total}}",
    previousPage: "Previous page",
    nextPage: "Next page",
    sortAscending: "Sort {{column}} ascending",
    sortDescending: "Sort {{column}} descending",
  },
  access: {
    title: "Access restricted",
    description:
      "Admin configuration is available only to users with the Admin role.",
    returnToDashboard: "Return to dashboard",
  },
  auth: {
    workspace: "Secure adjuster workspace",
    headline: "Review evidence with clear human control.",
    description:
      "Vehicle damage findings, supporting documents and AI conclusions stay organized in one operational workspace.",
    authorizedOnly: "Authorized local demonstration access only",
    signInTitle: "Sign in to Claim Assistant",
    signInDescription: "Use your account to continue.",
    signInFailed: "Sign-in failed",
    unableToSignIn: "Unable to sign in",
    email: "Email",
    password: "Password",
    emailPlaceholder: "name@company.com",
    signIn: "Sign in",
  },
  admin: {
    eyebrow: "Administration",
    title: "Assessment rules",
    description: "Global PoC rules applied to new vehicle damage analyses.",
    globalConfiguration: "Global configuration",
    activeThresholds: "Active thresholds",
    thresholdDescription:
      "Changes apply only to analyses started after the update.",
    configurationUnavailable: "Configuration unavailable",
    configurationLoadFailed: "Assessment rules could not be loaded.",
    rulesNotSaved: "Rules were not saved",
    thresholdRangeError: "Damage thresholds must be between 0 and 100.",
    thresholdOrderError:
      "Repair maximum must be lower than the replacement minimum.",
    updateFailed: "Unable to update assessment rules.",
    repairMaximum: "Repair maximum",
    replacementMinimum: "Replacement minimum",
    damagePercentage: "Damage percentage",
    lastChanged: "Last changed by {{user}} on {{date}}",
    systemDefaults: "system defaults",
    saveRules: "Save rules",
    changeHistory: "Change history",
    historyDescription: "Persisted audit trail for assessment-rule updates.",
    historyUnavailable: "History unavailable",
    activeRulesUnaffected: "The active rules are unaffected.",
    noHistory: "No administrator changes have been recorded.",
    historyChange:
      "Repair {{oldRepair}}% to {{newRepair}}%; replacement {{oldReplacement}}% to {{newReplacement}}%.",
  },
  claim: {
    intake: "Claim intake",
    createTitle: "Create a claim case",
    createDescription:
      "Start an evidence review case. This does not approve or reject an insurance claim.",
    information: "Claim information",
    informationDescription:
      "Claimant, vehicle and incident facts used throughout the review.",
    workflow: "Claim workflow",
    layoutMode: "Workflow layout",
    singlePage: "Single page",
    tabLayout: "Tabs",
    current: "Current",
    available: "Available",
    blocked: "Blocked",
    completed: "Completed",
    warning: "Warning",
    error: "Error",
    stepEvidence: "Evidence & documents",
    stepAnalysis: "Analysis",
    stepAiReview: "AI review",
    stepHumanReview: "Human review",
    vehicleAndClaimant: "Vehicle and claimant",
    vehicleDescription:
      "Basic case metadata for the upcoming evidence workflow.",
    claimantName: "Claimant name",
    vehicleMake: "Vehicle make",
    vehicleModel: "Vehicle model",
    vehicleYear: "Year",
    licensePlate: "License plate",
    vin: "VIN",
    searchMakes: "Search vehicle manufacturers",
    selectMake: "Select a vehicle make",
    selectMakeRequired: "Select a vehicle make before creating the claim.",
    loadingMakes: "Loading vehicle manufacturers...",
    noMakes: "No vehicle manufacturers are available.",
    unableToLoadMakes: "Vehicle manufacturers could not be loaded.",
    unableToCreate: "Unable to create claim",
    updateFailed: "Claim information could not be saved",
    cancel: "Cancel",
    create: "Create claim",
    backToClaims: "Back to claims",
    incidentInformation: "Incident information",
    incidentDescription: "Record when and where the incident happened.",
    incidentAt: "Incident date and time",
    incidentAtMustBePast: "Incident date and time must be earlier than now.",
    incidentLocation: "Incident location",
    incidentDetails: "Incident description",
    unavailable: "Claim unavailable",
    loadFailed: "The claim could not be loaded.",
    case: "Claim case",
    claimNumber: "Claim {{id}}",
    createdFor: "Created for {{name}}",
    deleteClaim: "Delete claim",
    deleteClaimTitle: "Delete this claim?",
    deleteClaimDescription:
      "Permanently delete claim {{id}}, its uploaded files, analysis, and review history? This cannot be undone.",
    deleteFailed: "Claim could not be deleted",
    safetyTitle: "Decision-support boundary",
    safetyDescription:
      "AI and human review statuses describe the evidence review only. They are not a final insurance claim decision.",
    status: {
      DRAFT: "Draft",
      SUBMITTED: "Submitted",
      ANALYZING: "Analyzing",
      REVIEW_REQUIRED: "Review required",
      AI_APPROVED: "AI review approved",
      AI_REJECTED: "AI review rejected",
      FAILED: "Failed",
    },
  },
  evidence: {
    description: "Upload each required evidence type in its dedicated section.",
    uploadFailed: "Evidence upload failed",
    otherDocuments: "Other documents",
    otherDescription:
      "Add optional supporting documents with a clear group name.",
    documentName: "Document name",
    files: "Files",
    otherFiles: "Other document files",
    addOther: "Add other document",
    uploaded: "Uploaded",
    analysisRequired: "Analysis required",
    required: "Required",
    addMore: "Add files",
    selectFiles: "Select files",
    selectFor: "Select files for {{category}}",
    removeFile: "Remove {{filename}}",
    openImage: "View {{filename}}",
    closeImage: "Close image",
    deleteAction: "Delete",
    deleteFailed: "Evidence could not be deleted",
    confirmDeleteTitle: "Delete evidence?",
    confirmDeleteDescription:
      "Delete {{filename}} from the current claim evidence? Previous analysis history will be preserved.",
    categories: {
      VEHICLE_DAMAGE_IMAGE: "Vehicle damage images",
      ID_CARD: "ID cards",
      INSURANCE_POLICY: "Insurance policies",
      VEHICLE_REGISTRATION: "Vehicle registrations",
      DRIVER_LICENSE: "Driver licenses",
      OTHER_DOCUMENT: "Other documents",
    },
    hints: {
      VEHICLE_DAMAGE_IMAGE: "One or more clear views of damaged areas.",
      ID_CARD: "Identity document for the claimant.",
      INSURANCE_POLICY: "Active policy pages relevant to this claim.",
      VEHICLE_REGISTRATION: "Vehicle ownership and registration details.",
      DRIVER_LICENSE: "Valid driver license images.",
      OTHER_DOCUMENT: "Additional supporting evidence.",
    },
  },
  analysis: {
    description:
      "Damage and document processing runs independently in the background.",
    analyze: "Analyze",
    runAgain: "Run analysis again",
    runAllAgain: "Run all analysis again",
    startFailed: "Analysis could not start",
    notReady: "Analysis is not ready",
    incidentMissing: "Complete incident information first.",
    evidenceMissing:
      "{{count}} required evidence section(s) are still missing.",
    processing: "Analysis is running in the background",
    processingDescription:
      "You can leave this page and return later. Status refreshes automatically.",
    inputsChanged: "Claim inputs changed",
    inputsChangedDescription:
      "Information or evidence changed after this run. Run analysis again before AI review.",
    partial: "Partial results available",
    partialDescription:
      "Some categories failed, but successful results remain available for review.",
    failed: "Analysis failed",
    empty: "No analysis has been started.",
    vehicleDamage: "Vehicle damage",
    damageDescription:
      "Normalized findings from the configured damage-model adapter.",
    reviewNote: "Review note",
    areaUnknown: "Vehicle area not identified",
    damageUnknown: "Damage type not identified",
    damage: "Damage",
    confidence: "Confidence",
    damageTable: "Vehicle damage findings",
    annotatedEvidence: "Annotated damage evidence",
    part: "Part",
    damageType: "Damage type",
    areaPercent: "Area %",
    noDamage: "No significant damage detections",
    noDamageMatches: "No damage findings match the selected filters.",
    findingShown: "finding shown",
    findingsShown: "findings shown",
    searchFindings: "Search findings",
    searchFindingsPlaceholder: "Part or damage type",
    allDamageTypes: "All damage types",
    status: {
      PENDING: "Pending",
      PROCESSING: "Processing",
      COMPLETED: "Completed",
      PARTIAL: "Partial",
      FAILED: "Failed",
    },
    assessment: {
      NO_DAMAGE: "No significant damage",
      REPAIR_LIKELY: "Repair likely",
      REPLACEMENT_LIKELY: "Replacement likely",
      MANUAL_INSPECTION_REQUIRED: "Manual inspection required",
    },
  },
  documents: {
    title: "Document analysis",
    description:
      "Review OCR and field validation results against each source image.",
    runContext: "Analysis run #{{id}}",
    imageCount: "{{count}} image(s)",
    processedBy: "Processed by {{adapter}}",
    processingState: "Waiting for OCR processing",
    processing: "OCR and field validation are processing.",
    reusing: "Reusing the previous analysis result.",
    reused: "Reused",
    unavailable: "Unavailable",
    noEvidence: "No evidence image is available in this category.",
    resultUnavailable:
      "No OCR result is available for this image. Run analysis again.",
    noFields: "OCR completed, but no validated fields were returned.",
    noExtractedFields:
      "Extraction completed, but no document fields were returned.",
    rerunHint: "Run analysis again to retry this image.",
    fieldsLocked:
      "Field values are locked because an AI review already exists for this analysis run.",
    saveFailed: "The reviewed field value could not be saved.",
    saveAll: "Save all fields",
    saveAllSuccess: "All document field values were saved.",
    saveAllFailed: "Document field values could not be saved.",
    saveAllBlocked: "Resolve these issues before saving the analysis",
    blockReasons: {
      SNAPSHOT_MISSING: "Save all confirmed document values before AI review.",
      SNAPSHOT_STALE: "The confirmed analysis is stale. Save all fields again.",
      INPUTS_CHANGED:
        "Claim information or evidence changed. Run analysis again.",
      DAMAGE_ANALYSIS_UNAVAILABLE: "Vehicle damage analysis is unavailable.",
      DOCUMENT_CATEGORY_MISSING: "{{category}} is missing.",
      DOCUMENT_CATEGORY_FAILED: "{{category}} did not complete successfully.",
      REQUIRED_VALUE_MISSING: "{{field}} requires a confirmed value.",
      COMPARISON_MISMATCH: "{{field}} does not match Claim Information.",
      COMPARISON_UNAVAILABLE:
        "{{field}} cannot be compared with Claim Information.",
      EXPIRY_DATE_INVALID: "{{field}} must use DD/MM/YYYY or YYYY-MM-DD.",
      EXPIRY_DATE_NOT_FUTURE: "{{field}} must be later than today.",
    },
    rawOcr: "Raw OCR text",
    structuredExtraction: "Structured extraction",
    reviewNotice:
      "Information was extracted automatically. Review and correct values before AI review.",
    extractionProvenance: "Prompt {{prompt}} · Schema {{schema}}",
    aiExtractedValue: "AI extracted value",
    confirmedValue: "Confirmed value",
    confirmedValueLabel: "{{field}} confirmed value",
    ocrValue: "OCR value",
    normalizedValue: "Normalized value",
    normalizedValueLabel: "{{field}} normalized value",
    comparedValues: "Claim: {{claim}} · Document: {{document}}",
    decisionBoundary:
      "Document validation supports adjuster review and is not a final insurance claim decision.",
    consistency: {
      MATCH: "Match",
      MISMATCH: "Mismatch",
      UNAVAILABLE: "Comparison unavailable",
    },
    consistencyExplanation: {
      MATCH: "The confirmed document value matches Claim Information.",
      MISMATCH:
        "The confirmed document value differs from Claim Information and requires manual review.",
      UNAVAILABLE:
        "A claim or confirmed document value is missing, so comparison is unavailable.",
    },
    consistencyUnavailable:
      "A claim or document value is missing, so this field could not be compared.",
    validationStatus: {
      VALID: "Valid",
      INVALID: "Invalid",
      UNCERTAIN: "Uncertain",
      MISSING: "Missing",
      LLM_UNAVAILABLE: "AI unavailable",
    },
    saveField: "Save {{field}}",
    originalValue: "Original AI value: {{value}}",
    fields: {
      full_name: "Full name",
      identity_number: "Identity number",
      date_of_birth: "Date of birth",
      place_of_origin: "Place of origin",
      expiry_date: "Expiry date",
      policy_number: "Policy number",
      insured_name: "Insured name",
      coverage_end: "Coverage end",
      vehicle_owner: "Vehicle owner",
      vehicle_brand: "Vehicle brand",
      vehicle_model: "Vehicle model",
      vehicle_type: "Vehicle type",
      owner_name: "Owner name",
      license_plate: "License plate",
      vehicle_make: "Vehicle make",
      license_number: "License number",
      holder_name: "Holder name",
      license_class: "License class",
    },
  },
  aiReview: {
    description:
      "Generate a structured review from normalized claim, evidence, damage and document results.",
    run: "Run AI review",
    rerun: "Re-run AI review",
    generating: "AI review is generating",
    generatingDescription:
      "The assistant is preparing a structured review. Keep this page open while it completes.",
    waitingForAnalysis:
      "Analysis is still processing. AI review will be available when it completes.",
    revision: "AI review revision {{revision}}",
    failed: "AI review could not be generated",
    ready:
      "Analysis is ready. Run AI review when document corrections are complete.",
    blocked: "Complete analysis before AI review.",
    validity: "Analysis completeness score",
    validityDisclaimer:
      "Reflects non-blocking processing warnings. It is not generated by the LLM, does not indicate claim validity or approval likelihood, and never replaces adjuster review.",
    reviewRequired: "Review required",
    generated: "Generated",
    fallback: "Demo fallback",
    unavailable: "AI unavailable",
    translationLoading: "Preparing Vietnamese translation",
    translationUnavailable: "Vietnamese translation unavailable",
    translationFallback:
      "The original English AI Review is shown. Its status and review history are unchanged.",
    warnings: "Warnings",
    evidenceReferences: "Evidence references",
    assessmentInterpretation: "Assessment interpretation",
    damagedPartsSummary: "Damaged parts summary",
    documentConsistency: "Document consistency",
    recommendedNextStep: "Recommended next step",
    humanReviewRequired: "Human review is required",
  },
  humanReview: {
    description:
      "Approve or reject the AI review result. A review note is always required.",
    blocked: "Run AI review before submitting a human decision.",
    approve: "Approve AI review",
    reject: "Reject AI review",
    note: "Review note",
    reason: "Reason category",
    selectReason: "Select a reason",
    submit: "Submit human review",
    revertNote: "Reason for reverting",
    revert: "Revert review",
    reverted: "Reverted",
    rerunAfterRevert:
      "Claim information and evidence can be corrected. Run analysis and AI review again before another decision.",
    history: "AI review decision history",
    approved: "AI review approved",
    rejected: "AI review rejected",
    reviewedBy: "Reviewed by {{reviewer}} on {{date}}",
    reasonValue: "Reason: {{reason}}",
    revertValue: "Revert note: {{note}}",
    reasons: {
      DOCUMENT_INFORMATION_INCOMPLETE: "Document information incomplete",
      DOCUMENT_INFORMATION_INCORRECT: "Document information incorrect",
      DAMAGE_ASSESSMENT_ISSUE: "Damage assessment issue",
      DAMAGE_EVIDENCE_ISSUE: "Damage evidence issue",
      MISSING_EVIDENCE: "Missing evidence",
      INCORRECT_AI_CONCLUSION: "Incorrect AI conclusion",
      OTHER: "Other",
    },
  },
  manufacturers: {
    title: "Vehicle manufacturers",
    description: "Manage vehicle manufacturers available for new claim intake.",
    manufacturer: "Manufacturer",
    name: "Manufacturer name",
    editName: "Edit manufacturer {{name}}",
    status: "Status",
    actions: "Actions",
    active: "Active",
    disabled: "Disabled",
    add: "Add manufacturer",
    save: "Save manufacturer",
    enable: "Enable",
    disable: "Disable",
    empty: "No vehicle manufacturers found.",
    noMatches: "No manufacturers match the selected filters.",
    shownOne: "manufacturer shown",
    shownMany: "manufacturers shown",
    search: "Search manufacturers",
    searchPlaceholder: "Search by name",
    allStatuses: "All statuses",
    showing: "Showing {{first}}-{{last}} of {{total}} manufacturers",
    none: "No manufacturers to show",
    rowsPerPage: "Rows per page",
    page: "Page {{current}} of {{total}}",
    previousPage: "Previous page",
    nextPage: "Next page",
    unavailable: "Vehicle manufacturers unavailable.",
    loadError: "Vehicle manufacturers could not be loaded.",
    saveError: "Vehicle manufacturer could not be saved.",
  },
};

const vi = {
  chrome: {
    insuranceWorkspace: "Trợ lý AI hỗ trợ giám định bảo hiểm ô tô",
    workspace: "Khu vực làm việc",
    skipToContent: "Chuyển đến nội dung",
    openNavigation: "Mở menu điều hướng",
    closeNavigation: "Đóng menu điều hướng",
    lightTheme: "Chuyển sang giao diện sáng",
    darkTheme: "Chuyển sang giao diện tối",
    roles: {
      ADMIN: "Quản trị viên",
      ADJUSTER: "Giám định viên",
      USER: "Khách hàng",
    },
  },
  pricing: {
    staleRecommendation: "Khuyến nghị từ lần phân tích trước",
    staleDescription:
      "Khuyến nghị này dựa trên dữ liệu cũ. Hãy cập nhật và lưu kết quả phân tích, sau đó chạy lại bước Đánh giá AI.",
    recommendationTitle: "Đề xuất phương án từ AI dựa trên giá",
    recommendationDisclaimer:
      "Đề xuất dựa trên giá tham khảo giả lập, không làm thay đổi kết quả đánh giá hư hỏng. Giám định viên là người quyết định phương án cuối cùng.",
    recommendation: {
      SUPPORTS_REPAIR: "Phù hợp với phương án sửa chữa",
      SUPPORTS_REPLACEMENT: "Phù hợp với phương án thay thế",
      MANUAL_REVIEW: "Cần kiểm tra giá thủ công",
    },
    lookupFailed: "Chưa tra cứu được giá. Vui lòng thử lại sau.",
    title: "Tham khảo chi phí sửa chữa và thay thế",
    mockNotice:
      "Bảng giá minh họa tại Việt Nam (VNĐ). Chỉ để tham khảo, không phải báo giá của xưởng sửa chữa hay mức bồi thường.",
    assessment: "Đánh giá mức độ hư hỏng",
    independent: "Dựa trên hư hỏng đã xác nhận, không phụ thuộc vào giá.",
    repair_estimate: "Chi phí sửa chữa ước tính",
    replacement_part_price: "Giá phụ tùng thay thế",
    COMPLETE: "Đã đủ giá để tính tổng",
    INCOMPLETE: "Mới tính được phần đã có giá, chưa đủ để xác định tổng chi phí",
    UNAVAILABLE: "Chưa có dữ liệu giá phù hợp",
    unavailable: "Chưa có dữ liệu giá",
    missing: "Không tìm thấy giá khớp chính xác",
    parts: "bộ phận đã có giá",
    source: "Nguồn tham khảo",
    effective: "Ngày hiệu lực",
    retrieved: "Thời điểm lấy giá",
    breakdown: "So sánh giá theo từng bộ phận",
    humanDecision:
      "Giá chỉ mang tính tham khảo. Giám định viên là người quyết định phương án cuối cùng.",
  },
  myClaims: {
    eyebrow: "Quản lý hồ sơ",
    title: "Hồ sơ của tôi",
    description:
      "Theo dõi tình trạng xử lý và hoàn thiện hồ sơ nháp trước khi gửi.",
    newClaim: "Tạo hồ sơ mới",
    claim: "Hồ sơ",
    created: "Ngày tạo",
    status: "Trạng thái",
    action: "Thao tác",
    continue: "Tiếp tục hoàn thiện",
    submitted: "Đã gửi hồ sơ",
    empty: "Bạn chưa tạo hồ sơ nào.",
    loadFailed: "Chưa tải được danh sách hồ sơ của bạn.",
    evidenceCount: "Đã tải lên {{count}}/{{total}} loại giấy tờ và hình ảnh bắt buộc",
    submit: "Gửi hồ sơ",
    submitSuccess: "Gửi hồ sơ thành công",
    submitFailed: "Gửi hồ sơ không thành công",
  },
  customerAccount: {
    eyebrow: "Quản lý khách hàng",
    pageTitle: "Tài khoản khách hàng",
    pageDescription:
      "Tạo tài khoản để khách hàng tự chuẩn bị, gửi và theo dõi hồ sơ bồi thường.",
    userAccounts: "Tài khoản khách hàng",
    userAccountsDescription: "Cấp tài khoản cho khách hàng nộp hồ sơ trực tuyến.",
    createAccount: "Tạo tài khoản khách hàng",
    userFullName: "Họ và tên",
    createUser: "Tạo tài khoản khách hàng",
    userCreated: "Đã tạo tài khoản khách hàng",
    userCreateFailed: "Không thể tạo tài khoản khách hàng",
    listTitle: "Danh sách tài khoản khách hàng",
    listDescription: "Danh sách khách hàng có tài khoản để tạo và theo dõi hồ sơ.",
    status: "Trạng thái",
    active: "Đang hoạt động",
    inactive: "Ngừng hoạt động",
    empty: "Chưa có tài khoản khách hàng.",
    loadFailed: "Không thể tải danh sách tài khoản khách hàng.",
  },
  toast: {
    claimInformationSaved: "Lưu thông tin hồ sơ thành công",
    claimInformationSaveFailed: "Không thể lưu thông tin hồ sơ",
    evidenceUploaded: "Đã tải lên {{count}} tệp",
    evidenceUploadFailed: "Không thể tải tệp lên",
    evidenceDeleted: "Đã xóa tệp khỏi hồ sơ",
    evidenceDeleteFailed: "Không thể xóa tệp",
    analysisStarted: "Đã bắt đầu phân tích hồ sơ",
    analysisStartedDescription:
      "Hệ thống tiếp tục xử lý ngay cả khi bạn rời khỏi trang này.",
    analysisStartFailed: "Không thể bắt đầu phân tích",
    analysisCompleted: "Phân tích đã hoàn tất",
    analysisPartial: "Đã có kết quả phân tích, nhưng một số mục cần kiểm tra thêm",
    analysisFailed: "Không thể hoàn tất phân tích",
    documentFieldsSaved: "Đã lưu thông tin giấy tờ",
    documentFieldsSaveFailed: "Không thể lưu thông tin giấy tờ",
    documentFieldSaved: "Đã lưu thông tin {{field}}",
    documentFieldSaveFailed: "Không thể lưu thông tin {{field}}",
    aiReviewGenerated: "Đã tạo bản đánh giá từ AI",
    aiReviewFailed: "Không thể tạo bản đánh giá từ AI",
    humanReviewApproved: "Đã chấp thuận kết quả đánh giá của AI",
    humanReviewRejected: "Đã từ chối kết quả đánh giá của AI",
    humanReviewFailed: "Không thể lưu kết quả đánh giá của giám định viên",
    humanReviewReverted: "Đã hoàn tác đánh giá của giám định viên",
    humanReviewRevertFailed: "Không thể hoàn tác đánh giá của giám định viên",
    claimDeleted: "Đã xóa hồ sơ",
    claimDeleteFailed: "Không thể xóa hồ sơ",
    claimCreated: "Tạo hồ sơ thành công",
    claimCreateFailed: "Không thể tạo hồ sơ",
  },
  common: {
    backToTop: "Lên đầu trang",
    edit: "Chỉnh sửa",
    save: "Lưu",
    cancel: "Hủy",
    tryAgain: "Thử lại",
    notProvided: "Chưa cung cấp",
    clearFilters: "Xóa bộ lọc",
    sortAscending: "Sắp xếp {{column}} theo thứ tự tăng dần",
    sortDescending: "Sắp xếp {{column}} theo thứ tự giảm dần",
  },

  navigation: {
    primary: "Điều hướng chính",
    dashboard: "Tổng quan",
    claims: "Hồ sơ bồi thường",
    customerAccounts: "Tài khoản khách hàng",
    admin: "Quản trị hệ thống",
    signOut: "Đăng xuất",
  },

  language: {
    label: "Ngôn ngữ",
    english: "Tiếng Anh",
    vietnamese: "Tiếng Việt",
    switchToVietnamese: "Tiếng Việt",
    switchToEnglish: "English",
  },

  dashboard: {
    eyebrow: "Quản lý hồ sơ bồi thường",
    title: "Tổng quan xử lý hồ sơ",
    description:
      "Theo dõi tình trạng hồ sơ, nắm các trường hợp cần xem xét và truy cập nhanh tài liệu liên quan.",
    newClaim: "Tạo hồ sơ",
    totalClaims: "Tổng số hồ sơ",
    pendingReviews: "Chờ giám định viên xem xét",
    aiApproved: "Đánh giá AI được chấp thuận",
    aiRejected: "Đánh giá AI bị từ chối",
    statusOverview: "Tình trạng xử lý hồ sơ",
    statusOverviewDescription:
      "Số lượng hồ sơ theo từng trạng thái. Đánh giá từ AI chỉ mang tính hỗ trợ, không phải quyết định bồi thường.",
    loadError: "Chưa tải được dữ liệu tổng quan.",
    noActivity: "Chưa có dữ liệu hồ sơ",
    noActivityDescription:
      "Biểu đồ trạng thái sẽ hiển thị khi có hồ sơ trong hệ thống.",
    needsReview: "Hồ sơ cần xem xét",
    needsReviewDescription: "Những hồ sơ đang chờ giám định viên xem xét và đưa ra quyết định.",
    noReviewQueue: "Hiện không có hồ sơ nào đang chờ giám định viên xem xét.",
    recentClaims: "Hồ sơ mới cập nhật",
    recentDescription:
      "Hồ sơ cập nhật gần nhất được hiển thị trước. Có thể tìm kiếm và lọc theo trạng thái hoặc thời gian cập nhật.",
    noClaims: "Chưa có hồ sơ nào",
    noClaimsDescription: "Tạo hồ sơ mới để bắt đầu bổ sung giấy tờ và hình ảnh.",
  },

  claimsList: {
    eyebrow: "Hồ sơ bồi thường",
    title: "Danh sách hồ sơ",
    description: "Theo dõi các hồ sơ đang xử lý và xem giấy tờ, hình ảnh của từng hồ sơ.",
    allClaims: "Tất cả hồ sơ",
    allClaimsDescription: "Hiển thị hồ sơ theo thứ tự cập nhật mới nhất.",
    loadError: "Chưa tải được danh sách hồ sơ.",
  },

  queue: {
    loadFailed: "Chưa tải được danh sách hồ sơ",
    claim: "Hồ sơ",
    vehicle: "Phương tiện",
    reviewStatus: "Trạng thái đánh giá",
    lastUpdated: "Cập nhật lần cuối",
    empty: "Không tìm thấy hồ sơ phù hợp với điều kiện lọc.",
    clearFilters: "Xóa bộ lọc",
    claimShown: "hồ sơ hiển thị",
    claimsShown: "hồ sơ hiển thị",
    searchLabel: "Tìm hồ sơ",
    searchPlaceholder: "Mã hồ sơ, tên người yêu cầu hoặc thông tin xe",
    status: "Trạng thái",
    allStatuses: "Tất cả trạng thái",
    updated: "Ngày cập nhật",
    allDates: "Mọi thời điểm",
    today: "Hôm nay",
    last7Days: "7 ngày gần đây",
    last30Days: "30 ngày gần đây",
    showing: "Đang hiển thị {{first}}–{{last}} trên tổng số {{total}} hồ sơ",
    none: "Chưa có hồ sơ để hiển thị",
    rowsPerPage: "Số hồ sơ mỗi trang",
    page: "Trang {{current}} / {{total}}",
    previousPage: "Trang trước",
    nextPage: "Trang sau",
    sortAscending: "Sắp xếp {{column}} theo thứ tự tăng dần",
    sortDescending: "Sắp xếp {{column}} theo thứ tự giảm dần",
  },

  access: {
    title: "Bạn không có quyền truy cập",
    description: "Chỉ quản trị viên mới có quyền thay đổi cấu hình hệ thống.",
    returnToDashboard: "Về trang tổng quan",
  },

  auth: {
    workspace: "AI hỗ trợ giám định bảo hiểm ô tô",
    headline: "AI hỗ trợ phân tích hồ sơ. Giám định viên giữ quyền quyết định.",
    description:
      "Thông tin hồ sơ, hình ảnh hư hỏng, giấy tờ và nhận định từ AI được tập trung tại một nơi để bạn dễ dàng xem xét.",
    authorizedOnly:
      "Bản demo nội bộ chỉ dành cho người dùng được cấp quyền truy cập.",
    signInTitle: "Đăng nhập hệ thống Claim Assistant",
    signInDescription: "Đăng nhập bằng tài khoản quản trị viên hoặc giám định viên để tiếp tục.",
    signInFailed: "Đăng nhập không thành công",
    unableToSignIn: "Chưa thể đăng nhập",
    email: "Email",
    password: "Mật khẩu",
    emailPlaceholder: "ten@congty.com",
    signIn: "Đăng nhập",
  },

  admin: {
    eyebrow: "Quản trị",
    title: "Quy tắc đánh giá",
    description:
      "Thiết lập các quy tắc chung áp dụng cho những lần phân tích hư hỏng tiếp theo.",
    globalConfiguration: "Thiết lập chung",
    activeThresholds: "Ngưỡng đánh giá hiện tại",
    thresholdDescription:
      "Các thay đổi chỉ có hiệu lực với những lần phân tích bắt đầu sau khi lưu.",
    configurationUnavailable: "Hiện không thể truy cập cấu hình",
    configurationLoadFailed: "Không thể tải cấu hình đánh giá.",
    rulesNotSaved: "Các thay đổi chưa được lưu",
    thresholdRangeError: "Tỷ lệ hư hỏng phải nằm trong khoảng 0–100%.",
    thresholdOrderError:
      "Ngưỡng sửa chữa tối đa phải thấp hơn ngưỡng thay thế tối thiểu.",
    updateFailed: "Không thể lưu thay đổi quy tắc đánh giá.",
    repairMaximum: "Ngưỡng sửa chữa tối đa",
    replacementMinimum: "Ngưỡng thay thế tối thiểu",
    damagePercentage: "Tỷ lệ diện tích hư hỏng",
    lastChanged: "{{user}} cập nhật lần cuối vào {{date}}",
    systemDefaults: "Thiết lập mặc định của hệ thống",
    saveRules: "Lưu",
    changeHistory: "Lịch sử thay đổi",
    historyDescription:
      "Theo dõi những lần quản trị viên thay đổi quy tắc đánh giá.",
    historyUnavailable: "Không thể tải lịch sử thay đổi",
    activeRulesUnaffected: "Các quy tắc hiện tại vẫn được giữ nguyên.",
    noHistory: "Chưa có thay đổi quy tắc nào được ghi nhận.",
    historyChange:
      "Ngưỡng sửa chữa: {{oldRepair}}% → {{newRepair}}%; ngưỡng thay thế: {{oldReplacement}}% → {{newReplacement}}%.",
  },

  claim: {
    intake: "Tiếp nhận hồ sơ",
    createTitle: "Tạo hồ sơ bồi thường",
    createDescription:
      "Tạo hồ sơ để ghi nhận thông tin, giấy tờ và hình ảnh phục vụ việc xem xét yêu cầu bồi thường. Đây chưa phải bước chấp thuận hay từ chối bồi thường.",

    information: "Thông tin hồ sơ",
    informationDescription:
      "Thông tin người yêu cầu bồi thường, xe và sự cố sẽ được dùng trong các bước xử lý tiếp theo.",

    workflow: "Quy trình xử lý hồ sơ",
    layoutMode: "Cách hiển thị quy trình",
    singlePage: "Một trang",
    tabLayout: "Tabs",

    current: "Hiện tại",
    available: "Khả dụng",
    blocked: "Chưa thể truy cập",
    completed: "Hoàn tất",
    warning: "Cảnh báo",
    error: "Lỗi",

    stepEvidence: "Hình ảnh và giấy tờ",
    stepAnalysis: "Phân tích",
    stepAiReview: "Đánh giá từ AI",
    stepHumanReview: "Giám định viên đánh giá",

    vehicleAndClaimant: "Thông tin xe và người yêu cầu bồi thường",
    vehicleDescription:
      "Cung cấp thông tin xe và người yêu cầu bồi thường để xử lý hồ sơ.",

    claimantName: "Họ tên người yêu cầu bồi thường",
    vehicleMake: "Hãng xe",
    vehicleModel: "Mẫu xe",
    vehicleYear: "Năm sản xuất",
    licensePlate: "Biển số xe",
    vin: "Số VIN",

    searchMakes: "Tìm hãng xe",
    selectMake: "Chọn hãng xe",
    selectMakeRequired: "Vui lòng chọn hãng xe trước khi tạo hồ sơ.",
    loadingMakes: "Đang tải danh sách hãng xe...",
    noMakes: "Hiện chưa có hãng xe nào để lựa chọn.",
    unableToLoadMakes: "Không thể tải danh sách hãng xe.",

    unableToCreate: "Không thể tạo hồ sơ",
    updateFailed: "Không thể lưu thông tin hồ sơ",

    cancel: "Hủy",
    create: "Tạo hồ sơ",
    backToClaims: "Quay lại danh sách hồ sơ",

    incidentInformation: "Thông tin sự cố",
    incidentDescription: "Cung cấp thời gian, địa điểm và diễn biến sự cố.",
    incidentAt: "Thời điểm xảy ra sự cố",
    incidentAtMustBePast: "Thời điểm xảy ra sự cố phải trước thời điểm hiện tại.",
    incidentLocation: "Địa điểm xảy ra sự cố",
    incidentDetails: "Diễn biến sự cố",

    unavailable: "Không thể truy cập hồ sơ",
    loadFailed: "Không thể tải hồ sơ.",

    case: "Hồ sơ bồi thường",
    claimNumber: "Hồ sơ {{id}}",
    createdFor: "Người yêu cầu bồi thường: {{name}}",
    deleteClaim: "Xóa hồ sơ",
    deleteClaimTitle: "Xóa hồ sơ này?",
    deleteClaimDescription:
      "Bạn có chắc muốn xóa vĩnh viễn hồ sơ {{id}} cùng các tệp đính kèm, kết quả phân tích và lịch sử đánh giá? Thao tác này không thể hoàn tác.",
    deleteFailed: "Không thể xóa hồ sơ",

    safetyTitle: "Thông tin hỗ trợ giám định",
    safetyDescription:
      "Kết quả đánh giá từ AI và giám định viên chỉ phản ánh quá trình rà soát hồ sơ, không thay thế quyết định bồi thường chính thức.",

    status: {
      DRAFT: "Bản nháp",
      SUBMITTED: "Đã nộp",
      ANALYZING: "Đang phân tích",
      REVIEW_REQUIRED: "Chờ giám định viên xem xét",
      AI_APPROVED: "Đã chấp thuận đánh giá của AI",
      AI_REJECTED: "Đã từ chối đánh giá của AI",
      FAILED: "Xử lý không thành công",
    },
  },

  evidence: {
    description:
      "Tải lên đầy đủ giấy tờ và hình ảnh theo từng nhóm yêu cầu.",

    uploadFailed: "Không thể tải tệp lên",

    otherDocuments: "Giấy tờ khác",
    otherDescription:
      "Bạn có thể bổ sung giấy tờ khác và đặt tên nhóm để dễ theo dõi.",

    documentName: "Tên giấy tờ",
    files: "Tệp đính kèm",
    otherFiles: "Tệp đính kèm khác",

    addOther: "Bổ sung giấy tờ",

    uploaded: "Đã tải lên",
    analysisRequired: "Cần phân tích",
    required: "Bắt buộc",

    addMore: "Thêm tệp",
    selectFiles: "Chọn tệp",
    selectFor: "Chọn tệp thuộc nhóm {{category}}",
    removeFile: "Xóa {{filename}}",
    openImage: "Xem {{filename}}",
    closeImage: "Đóng ảnh",
    deleteAction: "Xóa",
    deleteFailed: "Không thể xóa tệp",
    confirmDeleteTitle: "Xóa tệp khỏi hồ sơ?",
    confirmDeleteDescription:
      "Bạn có muốn xóa {{filename}} khỏi hồ sơ? Kết quả của các lần phân tích trước vẫn được lưu.",

    categories: {
      VEHICLE_DAMAGE_IMAGE: "Ảnh chụp hư hỏng xe",
      ID_CARD: "Giấy tờ tùy thân",
      INSURANCE_POLICY: "Hợp đồng bảo hiểm",
      VEHICLE_REGISTRATION: "Giấy đăng ký xe",
      DRIVER_LICENSE: "Giấy phép lái xe",
      OTHER_DOCUMENT: "Giấy tờ khác",
    },

    hints: {
      VEHICLE_DAMAGE_IMAGE:
        "Tải lên một hoặc nhiều ảnh rõ nét, thể hiện các vị trí hư hỏng trên xe.",

      ID_CARD: "Ảnh giấy tờ tùy thân của người yêu cầu bồi thường.",

      INSURANCE_POLICY:
        "Các trang hợp đồng bảo hiểm liên quan đến hồ sơ và còn hiệu lực.",

      VEHICLE_REGISTRATION: "Giấy đăng ký xe thể hiện thông tin phương tiện và chủ sở hữu.",

      DRIVER_LICENSE: "Ảnh giấy phép lái xe còn hiệu lực.",

      OTHER_DOCUMENT: "Giấy tờ hoặc hình ảnh bổ sung phục vụ việc xem xét hồ sơ.",
    },
  },

  analysis: {
    description:
      "Hệ thống xử lý hình ảnh hư hỏng và giấy tờ theo hai luồng riêng biệt.",

    analyze: "Bắt đầu phân tích",
    runAgain: "Phân tích lại",
    runAllAgain: "Phân tích lại toàn bộ",

    startFailed: "Không thể bắt đầu phân tích",
    notReady: "Chưa thể thực hiện phân tích",

    incidentMissing: "Hãy bổ sung đầy đủ thông tin sự cố trước khi phân tích.",

    evidenceMissing: "Hồ sơ còn thiếu {{count}} loại giấy tờ hoặc hình ảnh bắt buộc.",

    processing: "Đang phân tích hồ sơ",
    processingDescription:
      "Hệ thống vẫn tiếp tục xử lý nếu bạn rời khỏi trang. Trạng thái sẽ được cập nhật tự động.",

    inputsChanged: "Thông tin hồ sơ đã được cập nhật",
    inputsChangedDescription:
      "Thông tin hoặc tệp đính kèm đã thay đổi sau lần phân tích gần nhất. Hãy phân tích lại trước khi chuyển sang bước Đánh giá AI.",

    partial: "Một phần kết quả đã sẵn sàng",
    partialDescription:
      "Một số mục chưa xử lý thành công. Bạn vẫn có thể xem những kết quả đã hoàn tất.",

    failed: "Không thể hoàn tất phân tích",
    empty: "Chưa có kết quả phân tích.",

    vehicleDamage: "Phân tích hư hỏng xe",
    damageDescription:
      "Kết quả nhận diện hư hỏng được tổng hợp và chuẩn hóa từ mô hình AI đang sử dụng.",

    reviewNote: "Ghi chú đánh giá",

    areaUnknown: "Chưa xác định được bộ phận trên xe",
    damageUnknown: "Chưa xác định được loại hư hỏng",

    damage: "Hư hỏng",
    confidence: "Độ tin cậy",
    damageTable: "Danh sách bộ phận bị hư hỏng",
    annotatedEvidence: "Ảnh đã đánh dấu vùng hư hỏng",
    part: "Bộ phận",
    damageType: "Loại hư hỏng",
    areaPercent: "Tỷ lệ diện tích hư hỏng (%)",

    noDamage: "Chưa phát hiện hư hỏng đáng kể",
    noDamageMatches: "Không tìm thấy hư hỏng phù hợp với bộ lọc.",
    findingShown: "hạng mục hư hỏng được hiển thị",
    findingsShown: "hạng mục hư hỏng được hiển thị",
    searchFindings: "Tìm theo hư hỏng",
    searchFindingsPlaceholder: "Nhập tên bộ phận hoặc loại hư hỏng",
    allDamageTypes: "Tất cả loại hư hỏng",

    status: {
      PENDING: "Đang chờ",
      PROCESSING: "Đang xử lý",
      COMPLETED: "Hoàn tất",
      PARTIAL: "Hoàn tất một phần",
      FAILED: "Không thành công",
    },

    assessment: {
      NO_DAMAGE: "Không có hư hỏng đáng kể",
      REPAIR_LIKELY: "Có thể sửa chữa",
      REPLACEMENT_LIKELY: "Có thể cần thay thế",
      MANUAL_INSPECTION_REQUIRED: "Cần giám định viên kiểm tra",
    },
  },

  documents: {
    title: "Kiểm tra và đối chiếu giấy tờ",

    description:
      "Kiểm tra nội dung trích xuất bằng OCR và đối chiếu với thông tin trên giấy tờ gốc.",
    runContext: "Kết quả phân tích lần #{{id}}",
    imageCount: "{{count}} ảnh",
    processedBy: "Công cụ xử lý: {{adapter}}",
    processingState: "Đang chờ nhận dạng văn bản",
    processing: "Hệ thống đang nhận dạng văn bản và kiểm tra các trường thông tin.",
    reusing: "Đang dùng lại kết quả từ lần phân tích trước.",
    reused: "Đã dùng lại kết quả trước",
    unavailable: "Tạm thời không khả dụng",
    noEvidence: "Chưa có ảnh nào trong nhóm giấy tờ này.",
    resultUnavailable:
      "Ảnh này chưa có kết quả nhận dạng văn bản. Hãy phân tích lại để thử lần nữa.",
    noFields: "OCR đã hoàn tất nhưng chưa xác thực được trường thông tin nào.",
    noExtractedFields:
      "Đã trích xuất văn bản nhưng chưa nhận diện được trường thông tin nào.",
    rerunHint: "Hãy phân tích lại để hệ thống xử lý lại ảnh này.",
    fieldsLocked:
      "Không thể chỉnh sửa vì kết quả phân tích này đã được sử dụng để tạo đánh giá AI.",
    saveFailed: "Không thể lưu thông tin đã kiểm tra.",
    saveAll: "Lưu tất cả thông tin",
    saveAllSuccess: "Đã lưu toàn bộ thông tin giấy tờ.",
    saveAllFailed: "Không thể lưu toàn bộ thông tin giấy tờ.",
    saveAllBlocked: "Bạn cần xử lý các vấn đề sau trước khi lưu kết quả phân tích:",
    blockReasons: {
      SNAPSHOT_MISSING:
        "Hãy lưu các thông tin giấy tờ đã xác nhận trước khi chuyển sang Đánh giá AI.",
      SNAPSHOT_STALE: "Thông tin đã xác nhận không còn khớp với dữ liệu mới. Hãy kiểm tra và lưu lại.",
      INPUTS_CHANGED:
        "Thông tin hồ sơ hoặc tệp đính kèm đã thay đổi. Hãy phân tích lại.",
      DAMAGE_ANALYSIS_UNAVAILABLE:
        "Chưa có kết quả phân tích hư hỏng xe.",
      DOCUMENT_CATEGORY_MISSING: "Chưa có kết quả phân tích cho {{category}}.",
      DOCUMENT_CATEGORY_FAILED: "Xử lý {{category}} không thành công.",
      REQUIRED_VALUE_MISSING: "Bạn cần xác nhận thông tin {{field}}.",
      COMPARISON_MISMATCH: "{{field}} không khớp với thông tin hồ sơ.",
      COMPARISON_UNAVAILABLE:
        "Chưa thể đối chiếu {{field}} với thông tin hồ sơ.",
      EXPIRY_DATE_INVALID:
        "{{field}} cần có định dạng DD/MM/YYYY hoặc YYYY-MM-DD.",
      EXPIRY_DATE_NOT_FUTURE: "{{field}} phải là ngày sau hôm nay.",
    },
    rawOcr: "Nội dung nhận dạng từ OCR",
    structuredExtraction: "Thông tin được trích xuất",
    reviewNotice:
      "Đây là dữ liệu trích xuất tự động. Hãy đối chiếu với giấy tờ gốc và chỉnh sửa nếu cần trước khi thực hiện Đánh giá AI.",
    extractionProvenance: "Prompt {{prompt}} · Schema {{schema}}",
    aiExtractedValue: "Thông tin AI trích xuất",
    confirmedValue: "Thông tin đã xác nhận",
    confirmedValueLabel: "Thông tin đã xác nhận: {{field}}",
    ocrValue: "Nội dung OCR",
    normalizedValue: "Thông tin đã chuẩn hóa",
    normalizedValueLabel: "Thông tin đã chuẩn hóa: {{field}}",
    comparedValues: "Hồ sơ: {{claim}} · Giấy tờ: {{document}}",
    decisionBoundary:
      "Kết quả đối chiếu giấy tờ chỉ hỗ trợ giám định viên rà soát hồ sơ, không thay thế quyết định bồi thường chính thức.",
    consistency: {
      MATCH: "Khớp",
      MISMATCH: "Không khớp",
      UNAVAILABLE: "Không thể đối chiếu",
    },
    consistencyExplanation: {
      MATCH: "Thông tin đã xác nhận trên giấy tờ trùng khớp với hồ sơ.",
      MISMATCH:
        "Thông tin đã xác nhận trên giấy tờ khác với hồ sơ. Cần kiểm tra và điều chỉnh nếu có sai sót.",
      UNAVAILABLE:
        "Chưa đủ dữ liệu trong hồ sơ hoặc giấy tờ đã xác nhận để thực hiện đối chiếu.",
    },
    consistencyUnavailable:
      "Chưa đủ thông tin từ hồ sơ hoặc giấy tờ để đối chiếu mục này.",
    validationStatus: {
      VALID: "Hợp lệ",
      INVALID: "Không hợp lệ",
      UNCERTAIN: "Cần kiểm tra thêm",
      MISSING: "Thiếu dữ liệu",
      LLM_UNAVAILABLE: "Hiện không thể sử dụng AI",
    },

    saveField: "Lưu {{field}}",

    originalValue: "Thông tin AI trích xuất ban đầu: {{value}}",

    fields: {
      full_name: "Họ và tên",
      identity_number: "Số giấy tờ tùy thân",
      date_of_birth: "Ngày sinh",
      place_of_origin: "Quê quán",
      expiry_date: "Ngày hết hạn",

      policy_number: "Số hợp đồng bảo hiểm",
      insured_name: "Tên người được bảo hiểm",
      coverage_end: "Ngày hết hạn bảo hiểm",
      vehicle_owner: "Chủ xe",
      vehicle_brand: "Hãng xe",
      vehicle_model: "Dòng xe / mẫu xe",
      vehicle_type: "Loại xe",

      owner_name: "Tên chủ sở hữu",
      license_plate: "Biển số xe",
      vehicle_make: "Hãng xe",

      license_number: "Số giấy phép lái xe",
      holder_name: "Họ tên người được cấp",
      license_class: "Hạng giấy phép lái xe",
    },
  },

  aiReview: {
    description:
      "AI tổng hợp thông tin hồ sơ, kết quả phân tích hư hỏng và đối chiếu giấy tờ để đưa ra nhận định hỗ trợ giám định viên.",

    run: "Tạo đánh giá bằng AI",

    rerun: "Tạo lại đánh giá bằng AI",

    generating: "AI đang tổng hợp kết quả đánh giá",

    generatingDescription:
      "Hệ thống đang tạo bản đánh giá. Vui lòng giữ trang này mở cho đến khi hoàn tất.",

    waitingForAnalysis:
      "Bước phân tích vẫn đang xử lý. Bạn có thể đánh giá bằng AI sau khi bước này hoàn tất.",

    revision: "Bản đánh giá AI số {{revision}}",

    failed: "Không thể tạo bản đánh giá từ AI",

    ready:
      "Kết quả phân tích đã sẵn sàng. Hãy kiểm tra, xác nhận và lưu thông tin giấy tờ trước khi chạy Đánh giá AI.",

    blocked: "Bạn cần hoàn tất bước phân tích trước khi sử dụng Đánh giá AI.",

    validity: "Điểm hoàn thiện phân tích",

    validityDisclaimer:
      "Điểm phản ánh số cảnh báo còn lại sau khi phân tích và được tính theo quy tắc cố định, không phải do AI tự chấm. Điểm không thể hiện xác suất hồ sơ hợp lệ hay được chấp thuận; giám định viên vẫn phải xem xét kết quả.",

    reviewRequired: "Chờ giám định viên xem xét",
    generated: "Đã tạo",
    fallback: "Kết quả mô phỏng dùng cho bản demo",
    unavailable: "Hiện không thể sử dụng AI",
    translationLoading: "Đang tạo bản dịch tiếng Việt",
    translationUnavailable: "Không thể chuyển kết quả sang tiếng Việt",
    translationFallback:
      "Hiện đang hiển thị bản đánh giá tiếng Anh gốc. Trạng thái và lịch sử đánh giá vẫn được giữ nguyên.",

    warnings: "Cảnh báo",
    evidenceReferences: "Giấy tờ và hình ảnh tham chiếu",
    assessmentInterpretation: "Nhận định về mức độ hư hỏng",
    damagedPartsSummary: "Tổng hợp các bộ phận bị hư hỏng",
    documentConsistency: "Kết quả đối chiếu giấy tờ",
    recommendedNextStep: "Hướng xử lý đề xuất",
    humanReviewRequired: "Bắt buộc có giám định viên xem xét",
  },

  humanReview: {
    description:
      "Giám định viên xem xét và chấp thuận hoặc từ chối đánh giá của AI. Mỗi lần đánh giá đều phải có ghi chú.",

    blocked:
      "Hãy hoàn tất bước Đánh giá AI trước khi ghi nhận ý kiến của giám định viên.",

    approve: "Chấp thuận đánh giá của AI",
    reject: "Từ chối đánh giá của AI",

    note: "Ghi chú đánh giá",

    reason: "Nhóm lý do từ chối",
    selectReason: "Chọn nhóm lý do",

    submit: "Lưu kết quả đánh giá",

    revertNote: "Ghi chú lý do hoàn tác",
    revert: "Hoàn tác đánh giá",
    reverted: "Đã hoàn tác",

    rerunAfterRevert:
      "Bạn có thể cập nhật thông tin hồ sơ và tệp đính kèm. Sau đó hãy phân tích lại và tạo đánh giá AI mới trước khi tiếp tục xem xét.",

    history: "Lịch sử đánh giá của giám định viên",

    approved: "Giám định viên đã chấp thuận đánh giá của AI",
    rejected: "Giám định viên đã từ chối đánh giá của AI",

    reviewedBy: "{{reviewer}} đã đánh giá vào {{date}}",

    reasonValue: "Lý do: {{reason}}",
    revertValue: "Ghi chú hoàn tác: {{note}}",

    reasons: {
      DOCUMENT_INFORMATION_INCOMPLETE: "Thông tin giấy tờ chưa đầy đủ",

      DOCUMENT_INFORMATION_INCORRECT: "Thông tin giấy tờ không chính xác",

      DAMAGE_ASSESSMENT_ISSUE: "Kết quả đánh giá hư hỏng cần kiểm tra lại",

      DAMAGE_EVIDENCE_ISSUE: "Hình ảnh hoặc tài liệu về hư hỏng chưa phù hợp",

      MISSING_EVIDENCE: "Thiếu giấy tờ hoặc hình ảnh cần thiết",

      INCORRECT_AI_CONCLUSION: "Nhận định của AI chưa chính xác",

      OTHER: "Khác",
    },
  },

  manufacturers: {
    title: "Hãng xe",

    description:
      "Quản lý các hãng xe được phép chọn khi tạo hồ sơ bồi thường.",

    manufacturer: "Hãng xe",
    name: "Tên hãng xe",
    editName: "Sửa thông tin hãng {{name}}",
    status: "Trạng thái",
    actions: "Thao tác",

    active: "Đang sử dụng",
    disabled: "Ngừng sử dụng",

    add: "Thêm hãng xe",
    save: "Lưu hãng xe",

    enable: "Kích hoạt",
    disable: "Ngừng sử dụng",

    empty: "Chưa có hãng xe nào trong hệ thống.",
    noMatches: "Không tìm thấy hãng xe phù hợp với bộ lọc.",
    shownOne: "hãng xe được hiển thị",
    shownMany: "hãng xe được hiển thị",
    search: "Tìm hãng xe",
    searchPlaceholder: "Tìm theo tên",
    allStatuses: "Tất cả trạng thái",
    showing: "Đang hiển thị {{first}}–{{last}} trên tổng số {{total}} hãng xe",
    none: "Chưa có hãng xe để hiển thị",
    rowsPerPage: "Số hãng xe mỗi trang",
    page: "Trang {{current}} / {{total}}",
    previousPage: "Trang trước",
    nextPage: "Trang sau",

    unavailable: "Chưa có dữ liệu danh sách hãng xe.",

    loadError: "Không thể tải danh sách hãng xe.",

    saveError: "Không thể lưu hãng xe.",
  },
};

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, vi: { translation: vi } },
  lng:
    initialLanguage === "vi" || initialLanguage === "en"
      ? initialLanguage
      : "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

export { languageStorageKey };
export default i18n;
