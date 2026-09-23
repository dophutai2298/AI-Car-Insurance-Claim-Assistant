import {
  CheckmarkOutline,
  Document,
  InProgress,
  Save,
  WarningAlt,
} from "@carbon/icons-react";
import { Alert, Button, Chip, Input, Label } from "@heroui/react";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { EvidenceImagePreview } from "./EvidencePanel";
import { ClaimsApiError } from "./claimsApi";
import {
  useUpdateDocumentExtractedFields,
  useUpdateDocumentFieldValidation,
} from "./useClaims";
import type {
  ClaimConsistencyCheck,
  AnalysisBlockedReason,
  ClaimDetail,
  DocumentExtractedField,
  DocumentFieldComparison,
  DocumentFieldValidation,
  DocumentOcrResult,
  EvidenceCategory,
  EvidenceItem,
  FieldValidationStatus,
  WorkflowAnalysisRun,
} from "./types";

const documentCategories: EvidenceCategory[] = [
  "ID_CARD",
  "INSURANCE_POLICY",
  "VEHICLE_REGISTRATION",
  "DRIVER_LICENSE",
];
const comparableFieldKeys = new Set([
  "full_name",
  "insured_name",
  "owner_name",
  "holder_name",
  "vehicle_owner",
  "vehicle_make",
  "vehicle_brand",
  "license_plate",
]);

export function DocumentAnalysisResults({
  claim,
  run,
}: {
  claim: ClaimDetail;
  run: WorkflowAnalysisRun;
}) {
  const { t } = useTranslation();
  const results = run.document_ocr_results ?? [];
  const checks = run.consistency_checks ?? [];
  const editable = !run.damage_analysis?.copilot_conclusion;
  const extractedFields = results.flatMap(
    (result) => result.extraction?.fields ?? [],
  );
  const extractedFieldIds = extractedFields.map((field) => field.id).join(",");
  const [draftValues, setDraftValues] = useState<Record<number, string>>({});
  const saveAll = useUpdateDocumentExtractedFields(claim.id, run.id);
  useEffect(() => {
    setDraftValues((current) =>
      Object.fromEntries(
        extractedFields.map((field) => [
          field.id,
          Object.hasOwn(current, field.id)
            ? current[field.id]
            : (field.confirmed_value ?? ""),
        ]),
      ),
    );
    saveAll.reset();
  }, [extractedFieldIds, run.id]);
  const draftBlockedReasons = useMemo(
    () =>
      run.analysis_readiness
        ? getDraftBlockedReasons(claim, run, extractedFields, draftValues)
        : [],
    [claim, draftValues, extractedFieldIds, run],
  );
  const serverBlockedReasons =
    saveAll.error instanceof ClaimsApiError
      ? saveAll.error.blockedReasons
      : [];
  const blockedReasons = serverBlockedReasons.length
    ? serverBlockedReasons
    : draftBlockedReasons;
  const blockedByField = new Map(
    blockedReasons
      .filter((reason) => reason.field_id !== null)
      .map((reason) => [reason.field_id, reason]),
  );

  return (
    <section className="grid gap-5 border-t border-slate-200 pt-5">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-950">
            {t("documents.title")}
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            {t("documents.description")}
          </p>
        </div>
        <p className="text-xs text-slate-500">
          {t("documents.runContext", { id: run.id })}
        </p>
      </div>
      {!editable ? (
        <div className="border-l-2 border-slate-400 bg-slate-50 px-4 py-3 text-xs text-slate-700">
          {t("documents.fieldsLocked")}
        </div>
      ) : null}

      <div className="grid gap-6">
        {documentCategories.map((category) => {
          const categoryEvidence = claim.evidence.filter(
            (item) => item.category === category,
          );
          const categoryResults = results.filter(
            (result) => result.document_type === category,
          );
          return (
            <DocumentCategoryResults
              category={category}
              checks={checks}
              claimId={claim.id}
              editable={editable}
              evidence={categoryEvidence}
              draftValues={draftValues}
              blockedByField={blockedByField}
              isRunActive={["PENDING", "PROCESSING"].includes(run.status)}
              key={category}
              onDraftChange={(fieldId, value) => {
                saveAll.reset();
                setDraftValues((current) => ({
                  ...current,
                  [fieldId]: value,
                }));
              }}
              results={categoryResults}
            />
          );
        })}
      </div>

      {extractedFields.length ? (
        <div className="grid gap-3 border-t border-slate-200 pt-4">
          {blockedReasons.length ? (
            <Alert status="warning">
              <WarningAlt size={17} />
              <Alert.Title>{t("documents.saveAllBlocked")}</Alert.Title>
              <Alert.Description>
                <ul className="mt-1 list-disc space-y-1 pl-4">
                  {blockedReasons.map((reason, index) => (
                    <li key={`${reason.code}-${reason.field_id ?? index}`}>
                      {t(`documents.blockReasons.${reason.code}`, {
                        defaultValue: reason.message,
                        field: reason.field_key
                          ? t(`documents.fields.${reason.field_key}`, {
                              defaultValue: reason.field_key,
                            })
                          : "",
                        category: reason.category
                          ? t(`evidence.categories.${reason.category}`)
                          : "",
                      })}
                    </li>
                  ))}
                </ul>
              </Alert.Description>
            </Alert>
          ) : null}
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div aria-live="polite" className="text-xs">
              {saveAll.isSuccess ? (
                <span className="text-emerald-700">
                  {t("documents.saveAllSuccess")}
                </span>
              ) : saveAll.error ? (
                <span className="text-red-700">
                  {saveAll.error instanceof ClaimsApiError
                    ? saveAll.error.message
                    : t("documents.saveAllFailed")}
                </span>
              ) : null}
            </div>
            <Button
              isDisabled={
                !editable ||
                blockedReasons.length > 0 ||
                ["PENDING", "PROCESSING"].includes(run.status)
              }
              isPending={saveAll.isPending}
              onPress={() =>
                saveAll.mutate(
                  extractedFields.map((field) => ({
                    id: field.id,
                    confirmed_value: draftValues[field.id]?.trim() || null,
                  })),
                )
              }
              variant="primary"
            >
              <Save size={16} />
              {t("documents.saveAll")}
            </Button>
          </div>
        </div>
      ) : null}

      <div className="border-l-2 border-slate-300 bg-slate-50 px-4 py-3 text-xs text-slate-600">
        {t("documents.decisionBoundary")}
      </div>
    </section>
  );
}

function DocumentCategoryResults({
  category,
  evidence,
  results,
  checks,
  isRunActive,
  claimId,
  editable,
  draftValues,
  onDraftChange,
  blockedByField,
}: {
  category: EvidenceCategory;
  evidence: EvidenceItem[];
  results: DocumentOcrResult[];
  checks: ClaimConsistencyCheck[];
  isRunActive: boolean;
  claimId: string;
  editable: boolean;
  draftValues: Record<number, string>;
  onDraftChange: (fieldId: number, value: string) => void;
  blockedByField: Map<number | null, AnalysisBlockedReason>;
}) {
  const { t } = useTranslation();
  const resultsByEvidence = new Map(
    results.map((result) => [result.source_evidence_id, result]),
  );
  const orphanResults = results.filter(
    (result) => !evidence.some((item) => item.id === result.source_evidence_id),
  );
  const extraction = results.find((result) => result.extraction)?.extraction;

  return (
    <section aria-label={t(`evidence.categories.${category}`)}>
      <div className="mb-3 flex items-center justify-between gap-3 border-b border-slate-100 pb-2">
        <div className="flex items-center gap-2">
          <Document className="text-slate-500" size={17} />
          <h4 className="text-sm font-semibold text-slate-900">
            {t(`evidence.categories.${category}`)}
          </h4>
        </div>
        <span className="text-xs text-slate-500">
          {t("documents.imageCount", { count: evidence.length })}
        </span>
      </div>
      {evidence.length || orphanResults.length ? (
        <div className="grid gap-4 border-b border-slate-100 pb-4">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {evidence.map((item) => (
              <DocumentImageResult
                checks={checks}
                claimId={claimId}
                editable={editable}
                evidence={item}
                isRunActive={isRunActive}
                key={item.id}
                result={resultsByEvidence.get(item.id)}
              />
            ))}
            {orphanResults.map((result) => (
              <DocumentImageResult
                checks={checks}
                claimId={claimId}
                editable={editable}
                isRunActive={isRunActive}
                key={result.id}
                result={result}
              />
            ))}
          </div>
          {extraction ? (
            <ExtractionResult
              draftValues={draftValues}
              editable={editable}
              extraction={extraction}
              blockedByField={blockedByField}
              onDraftChange={onDraftChange}
            />
          ) : null}
        </div>
      ) : (
        <div className="border border-dashed border-slate-300 bg-slate-50 px-4 py-5 text-sm text-slate-500">
          {t("documents.noEvidence")}
        </div>
      )}
    </section>
  );
}

function DocumentImageResult({
  evidence,
  result,
  checks,
  isRunActive,
  claimId,
  editable,
}: {
  evidence?: EvidenceItem;
  result?: DocumentOcrResult;
  checks: ClaimConsistencyCheck[];
  isRunActive: boolean;
  claimId: string;
  editable: boolean;
}) {
  const { t } = useTranslation();
  const filename =
    result?.original_filename ?? evidence?.original_filename ?? "";
  const awaitingReuse = Boolean(
    !result && isRunActive && evidence && !evidence.analysis_required,
  );
  const status = result?.status ?? (isRunActive ? "PROCESSING" : "UNAVAILABLE");
  const fieldChecks = new Map(
    checks
      .filter(
        (check) => check.source_evidence_id === result?.source_evidence_id,
      )
      .map((check) => [check.field_validation_id, check]),
  );

  return (
    <article
      aria-label={filename}
      className="min-w-0 overflow-hidden rounded-lg border border-slate-200 bg-white"
    >
      <header className="grid grid-cols-[5.5rem_minmax(0,1fr)] gap-3 border-b border-slate-100 bg-slate-50/70 p-3">
        <div className="flex h-20 w-[5.5rem] items-center justify-center overflow-hidden rounded-md bg-slate-100 ring-1 ring-slate-200">
          {evidence?.content_type?.startsWith("image/") ? (
            <EvidenceImagePreview
              className="h-20 w-[5.5rem] object-cover"
              item={evidence}
            />
          ) : (
            <Document className="text-slate-400" size={24} />
          )}
        </div>
        <div className="min-w-0">
          <div className="flex items-start justify-between gap-2">
            <p
              className="truncate text-sm font-semibold text-slate-950"
              title={filename}
            >
              {filename}
            </p>
            <div className="flex shrink-0 items-center gap-1">
              {result?.reused || awaitingReuse ? (
                <Chip color="default" size="sm" variant="soft">
                  {t("documents.reused")}
                </Chip>
              ) : null}
              <StatusChip status={status} />
            </div>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            {awaitingReuse
              ? t("documents.reusing")
              : result?.adapter_name
                ? t("documents.processedBy", { adapter: result.adapter_name })
                : t("documents.processingState")}
          </p>
        </div>
      </header>

      <div className="grid gap-4 p-4">
        {!result && isRunActive ? (
          awaitingReuse ? (
            <ReuseState />
          ) : (
            <ProcessingState />
          )
        ) : null}
        {!result && !isRunActive ? (
          <EmptyResultState message={t("documents.resultUnavailable")} />
        ) : null}
        {result?.warning ? (
          <Alert status={result.status === "FAILED" ? "danger" : "warning"}>
            <WarningAlt size={17} />
            <Alert.Description>{result.warning}</Alert.Description>
          </Alert>
        ) : null}
        {result?.raw_text ? (
          <details className="group border border-slate-200 bg-slate-50">
            <summary className="cursor-pointer px-3 py-2 text-xs font-semibold text-slate-700">
              {t("documents.rawOcr")}
            </summary>
            <pre className="max-h-56 overflow-auto whitespace-pre-wrap border-t border-slate-200 bg-white p-3 font-mono text-xs leading-5 text-slate-700">
              {result.raw_text}
            </pre>
          </details>
        ) : null}
        {result?.field_validations.length ? (
          <div className="grid gap-3">
            {result.field_validations.map((field) => (
              <ValidatedField
                consistency={fieldChecks.get(field.id)}
                claimId={claimId}
                editable={editable}
                field={field}
                key={field.id}
              />
            ))}
          </div>
        ) : result?.status === "COMPLETED" && !result.extraction ? (
          <EmptyResultState message={t("documents.noFields")} />
        ) : null}
        {result?.status === "FAILED" ? (
          <p className="text-xs text-slate-500">{t("documents.rerunHint")}</p>
        ) : null}
      </div>
    </article>
  );
}

function ExtractionResult({
  extraction,
  editable,
  draftValues,
  onDraftChange,
  blockedByField,
}: {
  extraction: NonNullable<DocumentOcrResult["extraction"]>;
  editable: boolean;
  draftValues: Record<number, string>;
  onDraftChange: (fieldId: number, value: string) => void;
  blockedByField: Map<number | null, AnalysisBlockedReason>;
}) {
  const { t } = useTranslation();
  return (
    <section className="grid gap-3 border-t border-slate-100 pt-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h5 className="text-xs font-semibold text-slate-800">
            {t("documents.structuredExtraction")}
          </h5>
          <p className="mt-1 text-xs text-slate-500">
            {t("documents.extractionProvenance", {
              prompt: extraction.prompt_version,
              schema: extraction.schema_version,
            })}
          </p>
        </div>
        <div className="flex items-center gap-1">
          {extraction.reused ? (
            <Chip color="default" size="sm" variant="soft">
              {t("documents.reused")}
            </Chip>
          ) : null}
          <StatusChip status={extraction.status} />
        </div>
      </div>
      {extraction.warning ? (
        <Alert status="danger">
          <WarningAlt size={17} />
          <Alert.Description>{extraction.warning}</Alert.Description>
        </Alert>
      ) : null}
      <p className="border-l-2 border-cyan-500 bg-cyan-50 px-3 py-2 text-xs text-cyan-950">
        {t("documents.reviewNotice")}
      </p>
      {extraction.fields.length ? (
        <div className="grid gap-3">
          {extraction.fields.map((field) => (
            <ExtractedFieldEditor
              editable={editable}
              field={field}
              blockedReason={blockedByField.get(field.id)}
              key={field.id}
              onChange={(value) => onDraftChange(field.id, value)}
              value={draftValues[field.id] ?? field.confirmed_value ?? ""}
            />
          ))}
        </div>
      ) : extraction.status === "COMPLETED" ? (
        <EmptyResultState message={t("documents.noExtractedFields")} />
      ) : null}
    </section>
  );
}

function ExtractedFieldEditor({
  field,
  editable,
  value,
  onChange,
  blockedReason,
}: {
  field: DocumentExtractedField;
  editable: boolean;
  value: string;
  onChange: (value: string) => void;
  blockedReason?: AnalysisBlockedReason;
}) {
  const { t } = useTranslation();
  const label = t(`documents.fields.${field.field_key}`, {
    defaultValue: field.field_key,
  });

  return (
    <div className="grid gap-3 border-t border-slate-100 pt-3 first:border-t-0 first:pt-0">
      <h6 className="text-xs font-semibold text-slate-800">{label}</h6>
      <dl className="grid gap-3 text-xs sm:grid-cols-2">
        <ValueItem
          label={t("documents.aiExtractedValue")}
          value={field.ai_extracted_value}
        />
        <div className="min-w-0">
          <dt className="text-slate-500">{t("documents.confirmedValue")}</dt>
          <dd className="mt-1">
            <Label className="sr-only">
              {t("documents.confirmedValueLabel", { field: label })}
            </Label>
            <Input
              aria-label={t("documents.confirmedValueLabel", { field: label })}
              disabled={!editable}
              value={value}
              onChange={(event) => onChange(event.target.value)}
            />
          </dd>
        </div>
      </dl>
      {blockedReason ? (
        <div className="border-l-2 border-amber-500 bg-amber-50 px-3 py-2 text-xs text-amber-950">
          {t(`documents.blockReasons.${blockedReason.code}`, {
            defaultValue: blockedReason.message,
            field: label,
          })}
        </div>
      ) : null}
      {field.comparison &&
      value.trim() === (field.confirmed_value ?? "").trim() ? (
        <ConsistencyResult check={field.comparison} />
      ) : null}
    </div>
  );
}

function getDraftBlockedReasons(
  claim: ClaimDetail,
  run: WorkflowAnalysisRun,
  fields: DocumentExtractedField[],
  draftValues: Record<number, string>,
): AnalysisBlockedReason[] {
  const reasons = (run.analysis_readiness?.blocked_reasons ?? []).filter(
    (reason) =>
      reason.field_id === null &&
      !["SNAPSHOT_MISSING", "SNAPSHOT_STALE"].includes(reason.code),
  );
  for (const category of documentCategories) {
    const categoryFields = fields.filter((field) =>
      (run.document_ocr_results ?? []).some(
        (result) =>
          result.document_type === category &&
          result.extraction?.id === field.extraction_result_id,
      ),
    );
    for (const field of categoryFields) {
      const value = (draftValues[field.id] ?? field.confirmed_value ?? "").trim();
      if (!value) {
        reasons.push(
          blockedReason("REQUIRED_VALUE_MISSING", category, field),
        );
        continue;
      }
      const claimValue = claimValueForField(claim, field.field_key);
      if (
        claimValue !== null &&
        normalizeComparisonValue(claimValue) !== normalizeComparisonValue(value)
      ) {
        reasons.push(
          blockedReason("COMPARISON_MISMATCH", category, field),
        );
      }
    }
  }
  return reasons;
}

function claimValueForField(claim: ClaimDetail, fieldKey: string) {
  if (
    [
      "full_name",
      "insured_name",
      "owner_name",
      "holder_name",
      "vehicle_owner",
    ].includes(fieldKey)
  )
    return claim.claimant_name;
  if (["vehicle_make", "vehicle_brand"].includes(fieldKey)) return claim.vehicle.make;
  if (fieldKey === "license_plate") return claim.vehicle.license_plate;
  return null;
}

function normalizeComparisonValue(value: string) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLocaleLowerCase()
    .replace(/[^a-z0-9]/g, "");
}

function blockedReason(
  code: string,
  category: EvidenceCategory | null = null,
  field?: DocumentExtractedField,
): AnalysisBlockedReason {
  return {
    code,
    message: code,
    category,
    field_id: field?.id ?? null,
    field_key: field?.field_key ?? null,
  };
}

function ValidatedField({
  field,
  consistency,
  claimId,
  editable,
}: {
  field: DocumentFieldValidation;
  consistency?: ClaimConsistencyCheck;
  claimId: string;
  editable: boolean;
}) {
  const { t } = useTranslation();
  const update = useUpdateDocumentFieldValidation(
    claimId,
    field.analysis_run_id,
  );
  const [value, setValue] = useState(field.normalized_value ?? "");
  useEffect(
    () => setValue(field.normalized_value ?? ""),
    [field.normalized_value],
  );
  const label = t(`documents.fields.${field.field_key}`, {
    defaultValue: field.field_key,
  });
  const changed = value.trim() !== (field.normalized_value ?? "");
  return (
    <div className="grid gap-3 border-t border-slate-100 pt-3 first:border-t-0 first:pt-0">
      <div className="flex items-center justify-between gap-3">
        <h5 className="text-xs font-semibold text-slate-800">{label}</h5>
        <FieldStatusChip status={field.status} />
      </div>
      <dl className="grid gap-3 text-xs sm:grid-cols-3">
        <ValueItem label={t("documents.ocrValue")} value={field.ocr_value} />
        <div className="min-w-0">
          <dt className="text-slate-500">{t("documents.normalizedValue")}</dt>
          <dd className="mt-1 flex gap-2">
            <Label className="sr-only">
              {t("documents.normalizedValueLabel", { field: label })}
            </Label>
            <Input
              aria-label={t("documents.normalizedValueLabel", { field: label })}
              disabled={!editable}
              value={value}
              onChange={(event) => setValue(event.target.value)}
            />
            <Button
              aria-label={t("documents.saveField", { field: label })}
              isDisabled={!editable || !changed || !value.trim()}
              isIconOnly
              isPending={update.isPending}
              onPress={() =>
                update.mutate({
                  fieldValidationId: field.id,
                  reviewedValue: value,
                })
              }
              size="sm"
              variant="outline"
            >
              <CheckmarkOutline size={15} />
            </Button>
          </dd>
        </div>
        <ValueItem
          label={t("analysis.confidence")}
          value={`${Math.round(field.confidence * 100)}%`}
        />
      </dl>
      <p className="text-xs leading-5 text-slate-600">{field.summary}</p>
      {update.error ? (
        <div
          className="border-l-2 border-red-500 bg-red-50 px-3 py-2 text-xs text-red-900"
          role="alert"
        >
          {update.error instanceof ClaimsApiError
            ? update.error.message
            : t("documents.saveFailed")}
        </div>
      ) : null}
      {field.warnings.map((warning, index) => (
        <div
          className="flex gap-2 border-l-2 border-amber-400 bg-amber-50 px-3 py-2 text-xs text-amber-900"
          key={`${warning}-${index}`}
        >
          <WarningAlt className="mt-0.5 shrink-0" size={15} />
          <span>{warning}</span>
        </div>
      ))}
      {consistency ? <ConsistencyResult check={consistency} /> : null}
      {!consistency && comparableFieldKeys.has(field.field_key) ? (
        <div className="grid gap-1 border-l-2 border-slate-300 bg-slate-50 px-3 py-2 text-xs text-slate-700">
          <p className="font-semibold">
            {t("documents.consistency.UNAVAILABLE")}
          </p>
          <p>{t("documents.consistencyUnavailable")}</p>
        </div>
      ) : null}
    </div>
  );
}

function ConsistencyResult({
  check,
}: {
  check: ClaimConsistencyCheck | DocumentFieldComparison;
}) {
  const { t } = useTranslation();
  const matches = check.status === "MATCH";
  const unavailable = check.status === "UNAVAILABLE";
  return (
    <div
      className={`grid gap-1 border-l-2 px-3 py-2 text-xs ${
        matches
          ? "border-emerald-500 bg-emerald-50 text-emerald-900"
          : unavailable
            ? "border-slate-300 bg-slate-50 text-slate-700"
            : "border-amber-500 bg-amber-50 text-amber-950"
      }`}
    >
      <div className="flex items-center gap-2 font-semibold">
        {matches ? <CheckmarkOutline size={15} /> : <WarningAlt size={15} />}
        {t(`documents.consistency.${check.status}`)}
      </div>
      <p>{t(`documents.consistencyExplanation.${check.status}`)}</p>
      {check.claim_value && check.document_value ? (
        <p className="text-slate-600">
          {t("documents.comparedValues", {
            claim: check.claim_value,
            document: check.document_value,
          })}
        </p>
      ) : null}
    </div>
  );
}

function ValueItem({ label, value }: { label: string; value: string | null }) {
  const { t } = useTranslation();
  return (
    <div className="min-w-0">
      <dt className="text-slate-500">{label}</dt>
      <dd className="mt-1 break-words font-medium text-slate-900">
        {value || t("common.notProvided")}
      </dd>
    </div>
  );
}

function ProcessingState() {
  const { t } = useTranslation();
  return (
    <div className="flex items-center gap-3 bg-blue-50 px-3 py-3 text-xs text-blue-900">
      <InProgress className="animate-spin" size={17} />
      {t("documents.processing")}
    </div>
  );
}

function ReuseState() {
  const { t } = useTranslation();
  return (
    <div className="flex items-center gap-3 bg-slate-50 px-3 py-3 text-xs text-slate-700">
      <CheckmarkOutline size={17} />
      {t("documents.reusing")}
    </div>
  );
}

function EmptyResultState({ message }: { message: string }) {
  return (
    <div className="border border-dashed border-slate-300 bg-slate-50 px-3 py-4 text-xs text-slate-600">
      {message}
    </div>
  );
}

function StatusChip({
  status,
}: {
  status: DocumentOcrResult["status"] | "UNAVAILABLE";
}) {
  const { t } = useTranslation();
  const color =
    status === "COMPLETED"
      ? "success"
      : status === "FAILED" || status === "UNAVAILABLE"
        ? "danger"
        : status === "PARTIAL"
          ? "warning"
          : "default";
  return (
    <Chip color={color} size="sm" variant="soft">
      {status === "UNAVAILABLE"
        ? t("documents.unavailable")
        : t(`analysis.status.${status}`)}
    </Chip>
  );
}

function FieldStatusChip({ status }: { status: FieldValidationStatus }) {
  const { t } = useTranslation();
  const color =
    status === "VALID"
      ? "success"
      : status === "INVALID"
        ? "danger"
        : status === "UNCERTAIN" || status === "LLM_UNAVAILABLE"
          ? "warning"
          : "default";
  return (
    <Chip color={color} size="sm" variant="soft">
      {t(`documents.validationStatus.${status}`)}
    </Chip>
  );
}
