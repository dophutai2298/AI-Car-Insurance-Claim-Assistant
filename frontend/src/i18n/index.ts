import i18n from "i18next";
import { initReactI18next } from "react-i18next";

const languageStorageKey = "app.language";
const initialLanguage =
  typeof window !== "undefined"
    ? window.localStorage.getItem(languageStorageKey)
    : null;

const en = {
  common: {
    edit: "Edit",
    save: "Save",
    tryAgain: "Try again.",
    notProvided: "Not provided",
  },
  navigation: {
    dashboard: "Dashboard",
    claims: "Claims",
    admin: "Admin Config",
    signOut: "Sign out",
  },
  language: { switchToVietnamese: "Tiếng Việt", switchToEnglish: "English" },
  claim: {
    intake: "Claim intake",
    createTitle: "Create a claim case",
    createDescription:
      "Start an evidence review case. This does not approve or reject an insurance claim.",
    information: "Claim information",
    informationDescription:
      "Claimant, vehicle and incident facts used throughout the review.",
    workflow: "Claim workflow",
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
    incidentLocation: "Incident location",
    incidentDetails: "Incident description",
    unavailable: "Claim unavailable",
    loadFailed: "The claim could not be loaded.",
    case: "Claim case",
    claimNumber: "Claim {{id}}",
    createdFor: "Created for {{name}}",
    safetyTitle: "Decision-support boundary",
    safetyDescription:
      "AI and human review statuses describe the evidence review only. They are not a final insurance claim decision.",
    status: {
      DRAFT: "Draft",
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
    required: "Required",
    addMore: "Add files",
    selectFiles: "Select files",
    selectFor: "Select files for {{category}}",
    removeFile: "Remove {{filename}}",
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
    noDamage: "No significant damage detections",
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
      "Mock OCR values use the future adapter contract and can be corrected before AI review.",
    saveField: "Save {{field}}",
    originalValue: "Original AI value: {{value}}",
    fields: {
      full_name: "Full name",
      identity_number: "Identity number",
      date_of_birth: "Date of birth",
      policy_number: "Policy number",
      insured_name: "Insured name",
      coverage_end: "Coverage end",
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
    failed: "AI review could not be generated",
    ready:
      "Analysis is ready. Run AI review when document corrections are complete.",
    blocked: "Complete analysis before AI review.",
    validity: "Claim validity score",
    validityDisclaimer:
      "Decision-support score only. It is not an automatic approval probability.",
    reviewRequired: "Review required",
    generated: "Generated",
    fallback: "Demo fallback",
    unavailable: "AI unavailable",
    warnings: "Warnings",
    evidenceReferences: "Evidence references",
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
    unavailable: "Vehicle manufacturers unavailable.",
    loadError: "Vehicle manufacturers could not be loaded.",
    saveError: "Vehicle manufacturer could not be saved.",
  },
};

const vi = {
  common: {
    edit: "Chỉnh sửa",
    save: "Lưu",
    tryAgain: "Thử lại.",
    notProvided: "Chưa cung cấp",
  },

  navigation: {
    dashboard: "Tổng quan",
    claims: "Hồ sơ bồi thường",
    admin: "Cấu hình quản trị",
    signOut: "Đăng xuất",
  },

  language: {
    switchToVietnamese: "Tiếng Việt",
    switchToEnglish: "English",
  },

  claim: {
    intake: "Tiếp nhận hồ sơ",
    createTitle: "Tạo hồ sơ bồi thường",
    createDescription:
      "Bắt đầu quy trình xem xét bằng chứng. Thao tác này không đồng nghĩa với việc chấp thuận hoặc từ chối yêu cầu bồi thường.",

    information: "Thông tin hồ sơ",
    informationDescription:
      "Thông tin người yêu cầu, phương tiện và sự cố được sử dụng xuyên suốt quá trình xem xét.",

    workflow: "Quy trình xử lý hồ sơ",

    current: "Hiện tại",
    available: "Khả dụng",
    blocked: "Bị chặn",
    completed: "Hoàn tất",
    warning: "Cảnh báo",
    error: "Lỗi",

    stepEvidence: "Bằng chứng & giấy tờ",
    stepAnalysis: "Phân tích",
    stepAiReview: "Đánh giá AI",
    stepHumanReview: "Đánh giá thủ công",

    vehicleAndClaimant: "Phương tiện và người yêu cầu",
    vehicleDescription:
      "Thông tin cơ bản của hồ sơ phục vụ cho quy trình xử lý bằng chứng.",

    claimantName: "Tên người yêu cầu",
    vehicleMake: "Hãng xe",
    vehicleModel: "Dòng xe",
    vehicleYear: "Năm sản xuất",
    licensePlate: "Biển số xe",
    vin: "Số VIN",

    searchMakes: "Tìm kiếm hãng xe",
    selectMake: "Chọn hãng xe",
    selectMakeRequired: "Vui lòng chọn hãng xe trước khi tạo hồ sơ.",
    loadingMakes: "Đang tải danh sách hãng xe...",
    noMakes: "Không có hãng xe nào khả dụng.",
    unableToLoadMakes: "Không thể tải danh sách hãng xe.",

    unableToCreate: "Không thể tạo hồ sơ",
    updateFailed: "Không thể lưu thông tin hồ sơ",

    cancel: "Hủy",
    create: "Tạo hồ sơ",
    backToClaims: "Quay lại danh sách hồ sơ",

    incidentInformation: "Thông tin sự cố",
    incidentDescription: "Ghi nhận thời gian và địa điểm xảy ra sự cố.",
    incidentAt: "Ngày và giờ xảy ra sự cố",
    incidentLocation: "Địa điểm xảy ra sự cố",
    incidentDetails: "Mô tả sự cố",

    unavailable: "Hồ sơ không khả dụng",
    loadFailed: "Không thể tải hồ sơ.",

    case: "Hồ sơ bồi thường",
    claimNumber: "Hồ sơ {{id}}",
    createdFor: "Được tạo cho {{name}}",

    safetyTitle: "Giới hạn hỗ trợ ra quyết định",
    safetyDescription:
      "Trạng thái đánh giá của AI và người xử lý chỉ mô tả quá trình xem xét bằng chứng. Đây không phải là quyết định cuối cùng đối với yêu cầu bồi thường.",

    status: {
      DRAFT: "Bản nháp",
      ANALYZING: "Đang phân tích",
      REVIEW_REQUIRED: "Cần xem xét",
      AI_APPROVED: "Đánh giá AI đã được chấp thuận",
      AI_REJECTED: "Đánh giá AI đã bị từ chối",
      FAILED: "Thất bại",
    },
  },

  evidence: {
    description:
      "Tải từng loại bằng chứng bắt buộc lên đúng khu vực tương ứng.",

    uploadFailed: "Tải bằng chứng lên thất bại",

    otherDocuments: "Giấy tờ khác",
    otherDescription:
      "Thêm các giấy tờ hỗ trợ tùy chọn và đặt tên nhóm rõ ràng.",

    documentName: "Tên giấy tờ",
    files: "Tệp",
    otherFiles: "Tệp giấy tờ khác",

    addOther: "Thêm giấy tờ khác",

    uploaded: "Đã tải lên",
    required: "Bắt buộc",

    addMore: "Thêm tệp",
    selectFiles: "Chọn tệp",
    selectFor: "Chọn tệp cho {{category}}",
    removeFile: "Xóa {{filename}}",

    categories: {
      VEHICLE_DAMAGE_IMAGE: "Hình ảnh hư hỏng xe",
      ID_CARD: "Giấy tờ tùy thân",
      INSURANCE_POLICY: "Hợp đồng bảo hiểm",
      VEHICLE_REGISTRATION: "Giấy đăng ký xe",
      DRIVER_LICENSE: "Giấy phép lái xe",
      OTHER_DOCUMENT: "Giấy tờ khác",
    },

    hints: {
      VEHICLE_DAMAGE_IMAGE:
        "Một hoặc nhiều hình ảnh rõ nét về các khu vực bị hư hỏng.",

      ID_CARD: "Giấy tờ xác minh danh tính của người yêu cầu bồi thường.",

      INSURANCE_POLICY:
        "Các trang hợp đồng bảo hiểm còn hiệu lực liên quan đến hồ sơ này.",

      VEHICLE_REGISTRATION: "Thông tin đăng ký và chủ sở hữu phương tiện.",

      DRIVER_LICENSE: "Hình ảnh giấy phép lái xe còn hiệu lực.",

      OTHER_DOCUMENT: "Các bằng chứng hoặc giấy tờ hỗ trợ bổ sung.",
    },
  },

  analysis: {
    description:
      "Phân tích hư hỏng và xử lý giấy tờ được thực hiện độc lập trong nền.",

    analyze: "Phân tích",
    runAgain: "Phân tích lại",

    startFailed: "Không thể bắt đầu phân tích",
    notReady: "Phân tích chưa sẵn sàng",

    incidentMissing: "Vui lòng hoàn tất thông tin sự cố trước.",

    evidenceMissing: "Vẫn còn thiếu {{count}} loại bằng chứng bắt buộc.",

    processing: "Phân tích đang được xử lý trong nền",
    processingDescription:
      "Bạn có thể rời khỏi trang này và quay lại sau. Trạng thái sẽ được tự động cập nhật.",

    inputsChanged: "Dữ liệu hồ sơ đã thay đổi",
    inputsChangedDescription:
      "Thông tin hoặc bằng chứng đã thay đổi sau lần phân tích này. Vui lòng phân tích lại trước khi thực hiện đánh giá AI.",

    partial: "Có kết quả phân tích một phần",
    partialDescription:
      "Một số hạng mục xử lý thất bại, nhưng các kết quả thành công vẫn có thể được xem xét.",

    failed: "Phân tích thất bại",
    empty: "Chưa thực hiện phân tích.",

    vehicleDamage: "Hư hỏng phương tiện",
    damageDescription:
      "Các kết quả đã được chuẩn hóa từ mô hình phân tích hư hỏng được cấu hình.",

    reviewNote: "Ghi chú đánh giá",

    areaUnknown: "Không xác định được khu vực trên xe",
    damageUnknown: "Không xác định được loại hư hỏng",

    damage: "Hư hỏng",
    confidence: "Độ tin cậy",

    noDamage: "Không phát hiện hư hỏng đáng kể",

    status: {
      PENDING: "Đang chờ",
      PROCESSING: "Đang xử lý",
      COMPLETED: "Hoàn tất",
      PARTIAL: "Một phần",
      FAILED: "Thất bại",
    },

    assessment: {
      NO_DAMAGE: "Không có hư hỏng đáng kể",
      REPAIR_LIKELY: "Có khả năng cần sửa chữa",
      REPLACEMENT_LIKELY: "Có khả năng cần thay thế",
      MANUAL_INSPECTION_REQUIRED: "Cần kiểm tra thủ công",
    },
  },

  documents: {
    title: "Phân tích giấy tờ",

    description:
      "Dữ liệu OCR mô phỏng sử dụng cấu trúc của adapter trong tương lai và có thể được chỉnh sửa trước khi đánh giá AI.",

    saveField: "Lưu {{field}}",

    originalValue: "Giá trị AI ban đầu: {{value}}",

    fields: {
      full_name: "Họ và tên",
      identity_number: "Số giấy tờ tùy thân",
      date_of_birth: "Ngày sinh",

      policy_number: "Số hợp đồng bảo hiểm",
      insured_name: "Tên người được bảo hiểm",
      coverage_end: "Ngày hết hạn bảo hiểm",

      owner_name: "Tên chủ sở hữu",
      license_plate: "Biển số xe",
      vehicle_make: "Hãng xe",

      license_number: "Số giấy phép lái xe",
      holder_name: "Tên người được cấp",
      license_class: "Hạng giấy phép lái xe",
    },
  },

  aiReview: {
    description:
      "Tạo kết quả đánh giá có cấu trúc từ thông tin hồ sơ, bằng chứng, kết quả phân tích hư hỏng và giấy tờ.",

    run: "Thực hiện đánh giá AI",

    failed: "Không thể tạo kết quả đánh giá AI",

    ready:
      "Phân tích đã sẵn sàng. Hãy thực hiện đánh giá AI sau khi hoàn tất việc chỉnh sửa thông tin giấy tờ.",

    blocked: "Vui lòng hoàn tất phân tích trước khi thực hiện đánh giá AI.",

    validity: "Điểm hợp lệ của hồ sơ",

    validityDisclaimer:
      "Điểm số này chỉ hỗ trợ quá trình ra quyết định và không phải là xác suất hồ sơ được tự động chấp thuận.",

    reviewRequired: "Cần xem xét",
    generated: "Đã tạo",
    fallback: "Dữ liệu dự phòng cho demo",
    unavailable: "AI không khả dụng",

    warnings: "Cảnh báo",
    evidenceReferences: "Bằng chứng tham chiếu",
  },

  humanReview: {
    description:
      "Chấp thuận hoặc từ chối kết quả đánh giá của AI. Ghi chú đánh giá luôn là bắt buộc.",

    blocked:
      "Vui lòng thực hiện đánh giá AI trước khi gửi quyết định của người xử lý.",

    approve: "Chấp thuận đánh giá AI",
    reject: "Từ chối đánh giá AI",

    note: "Ghi chú đánh giá",

    reason: "Nhóm lý do",
    selectReason: "Chọn lý do",

    submit: "Gửi đánh giá",

    revertNote: "Lý do hoàn tác",
    revert: "Hoàn tác đánh giá",
    reverted: "Đã hoàn tác",

    rerunAfterRevert:
      "Thông tin hồ sơ và bằng chứng có thể được chỉnh sửa. Vui lòng chạy lại phân tích và đánh giá AI trước khi đưa ra quyết định mới.",

    history: "Lịch sử quyết định đánh giá AI",

    approved: "Đánh giá AI đã được chấp thuận",
    rejected: "Đánh giá AI đã bị từ chối",

    reviewedBy: "Được đánh giá bởi {{reviewer}} vào {{date}}",

    reasonValue: "Lý do: {{reason}}",
    revertValue: "Ghi chú hoàn tác: {{note}}",

    reasons: {
      DOCUMENT_INFORMATION_INCOMPLETE: "Thông tin giấy tờ chưa đầy đủ",

      DOCUMENT_INFORMATION_INCORRECT: "Thông tin giấy tờ không chính xác",

      DAMAGE_ASSESSMENT_ISSUE: "Có vấn đề với kết quả đánh giá hư hỏng",

      DAMAGE_EVIDENCE_ISSUE: "Có vấn đề với bằng chứng hư hỏng",

      MISSING_EVIDENCE: "Thiếu bằng chứng",

      INCORRECT_AI_CONCLUSION: "Kết luận của AI không chính xác",

      OTHER: "Khác",
    },
  },

  manufacturers: {
    title: "Hãng xe",

    description:
      "Quản lý danh sách hãng xe có thể sử dụng khi tạo hồ sơ bồi thường mới.",

    manufacturer: "Hãng xe",
    name: "Tên hãng xe",
    editName: "Chỉnh sửa hãng xe {{name}}",
    status: "Trạng thái",
    actions: "Thao tác",

    active: "Đang hoạt động",
    disabled: "Đã vô hiệu hóa",

    add: "Thêm hãng xe",
    save: "Lưu hãng xe",

    enable: "Kích hoạt",
    disable: "Vô hiệu hóa",

    empty: "Không tìm thấy hãng xe nào.",

    unavailable: "Danh sách hãng xe không khả dụng.",

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
