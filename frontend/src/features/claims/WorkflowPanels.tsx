import {
  Analytics,
  CheckmarkOutline,
  DataStructured,
  Document,
  Image,
  Reset,
  WarningAlt,
} from "@carbon/icons-react";
import {
  Alert,
  Button,
  Card,
  Chip,
  Input,
  Label,
  TextField,
} from "@heroui/react";
import { useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthProvider";
import {
  EvidenceImagePreview,
  requiredEvidenceCategories,
} from "./EvidencePanel";
import { ClaimsApiError } from "./claimsApi";
import { DocumentAnalysisResults } from "./DocumentAnalysisResults";
import {
  useRevertCopilotReview,
  useReviewCopilotConclusion,
  useWorkflowAiReview,
  useWorkflowAnalysis,
} from "./useClaims";
import type {
  ClaimDetail,
  CopilotConclusion,
  CopilotConclusionRejectionCategory,
  CopilotConclusionReview,
  DamageAnalysis,
  WorkflowAnalysisRun,
} from "./types";

export function AnalysisPanel({ claim }: { claim: ClaimDetail }) {
  const { t } = useTranslation();
  const start = useWorkflowAnalysis(claim.id);
  const run = claim.latest_analysis_run;
  const conclusion =
    run?.damage_analysis?.copilot_conclusion ??
    (!run ? claim.latest_damage_analysis?.copilot_conclusion : undefined);
  const activeReview = conclusion?.review_history[0];
  const missingEvidence = requiredEvidenceCategories.filter(
    (category) =>
      !(claim.evidence ?? []).some((item) => item.category === category),
  );
  const canStart =
    Boolean(claim.incident) &&
    missingEvidence.length === 0 &&
    !["PENDING", "PROCESSING"].includes(run?.status ?? "") &&
    !(activeReview && !activeReview.reverted_at);
  const statusColor =
    run?.status === "COMPLETED"
      ? "success"
      : run?.status === "PARTIAL"
        ? "warning"
        : run?.status === "FAILED"
          ? "danger"
          : "default";

  return (
    <Card
      className="rounded-lg border border-slate-200 bg-white shadow-sm"
      id="analysis"
    >
      <Card.Header className="flex flex-col gap-4 border-b border-slate-100 px-6 py-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-lg bg-indigo-50 text-indigo-700 ring-1 ring-indigo-100">
            <Analytics size={20} />
          </div>
          <div>
            <Card.Title className="text-lg text-slate-950">
              {t("claim.stepAnalysis")}
            </Card.Title>
            <Card.Description className="text-sm text-slate-500">
              {t("analysis.description")}
            </Card.Description>
          </div>
        </div>
        <div className="flex items-center gap-3">
          {run ? (
            <Chip color={statusColor} variant="soft">
              {t(`analysis.status.${run.status}`)}
            </Chip>
          ) : null}
          <Button
            isDisabled={!canStart}
            isPending={start.isPending}
            onPress={() => start.mutate()}
            variant="primary"
          >
            {run ? t("analysis.runAgain") : t("analysis.analyze")}
          </Button>
        </div>
      </Card.Header>
      <Card.Content className="grid gap-6 p-6">
        {start.error ? (
          <Alert status="danger">
            <Alert.Title>{t("analysis.startFailed")}</Alert.Title>
            <Alert.Description>
              {start.error instanceof ClaimsApiError
                ? start.error.message
                : t("common.tryAgain")}
            </Alert.Description>
          </Alert>
        ) : null}
        {!claim.incident || missingEvidence.length ? (
          <Alert status="warning">
            <WarningAlt size={18} />
            <Alert.Title>{t("analysis.notReady")}</Alert.Title>
            <Alert.Description>
              {!claim.incident
                ? t("analysis.incidentMissing")
                : t("analysis.evidenceMissing", {
                    count: missingEvidence.length,
                  })}
            </Alert.Description>
          </Alert>
        ) : null}
        {run && ["PENDING", "PROCESSING"].includes(run.status) ? (
          <div className="border-l-2 border-blue-500 bg-blue-50 p-4">
            <p className="text-sm font-semibold text-blue-950">
              {t("analysis.processing")}
            </p>
            <p className="mt-1 text-sm text-blue-800">
              {t("analysis.processingDescription")}
            </p>
          </div>
        ) : null}
        {run?.inputs_changed ? (
          <Alert status="warning">
            <WarningAlt size={18} />
            <Alert.Title>{t("analysis.inputsChanged")}</Alert.Title>
            <Alert.Description>
              {t("analysis.inputsChangedDescription")}
            </Alert.Description>
          </Alert>
        ) : null}
        {run?.status === "PARTIAL" ? (
          <Alert status="warning">
            <WarningAlt size={18} />
            <Alert.Title>{t("analysis.partial")}</Alert.Title>
            <Alert.Description>
              {t("analysis.partialDescription")}
            </Alert.Description>
          </Alert>
        ) : null}
        {run?.status === "FAILED" ? (
          <Alert status="danger">
            <Alert.Title>{t("analysis.failed")}</Alert.Title>
            <Alert.Description>
              {run.failure_reason ?? t("common.tryAgain")}
            </Alert.Description>
          </Alert>
        ) : null}
        {run?.damage_analysis ? (
          <DamageResults analysis={run.damage_analysis} />
        ) : null}
        {run ? <DocumentAnalysisResults claim={claim} run={run} /> : null}
        {!run ? (
          <p className="text-sm text-slate-500">{t("analysis.empty")}</p>
        ) : null}
      </Card.Content>
    </Card>
  );
}

function DamageResults({ analysis }: { analysis: DamageAnalysis }) {
  const { t } = useTranslation();
  const annotatedEvidence = Array.from(
    new Map(
      analysis.detections.map((detection) => [
        detection.annotated_evidence.id,
        detection.annotated_evidence,
      ]),
    ).values(),
  );

  return (
    <section className="grid gap-4">
      <div className="flex items-center justify-between border-b border-slate-100 pb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-950">
            {t("analysis.vehicleDamage")}
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            {t("analysis.damageDescription")}
          </p>
        </div>
        <Chip
          color={
            analysis.assessment === "REPLACEMENT_LIKELY"
              ? "danger"
              : analysis.assessment === "MANUAL_INSPECTION_REQUIRED"
                ? "warning"
                : "success"
          }
          size="sm"
          variant="soft"
        >
          {t(`analysis.assessment.${analysis.assessment}`)}
        </Chip>
      </div>
      {analysis.warning ? (
        <Alert status="warning">
          <WarningAlt size={18} />
          <Alert.Title>{t("analysis.reviewNote")}</Alert.Title>
          <Alert.Description>{analysis.warning}</Alert.Description>
        </Alert>
      ) : null}
      {analysis.detections.length ? (
        <div className="grid items-start gap-4 xl:grid-cols-[18rem_minmax(0,1fr)]">
          <div
            aria-label={t("analysis.annotatedEvidence")}
            className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1"
            role="group"
          >
            {annotatedEvidence.map((item) => (
              <figure
                className="overflow-hidden border border-slate-200 bg-slate-50"
                key={item.id}
              >
                <EvidenceImagePreview
                  className="h-44 w-full object-contain"
                  item={item}
                />
                <figcaption className="truncate border-t border-slate-200 bg-white px-3 py-2 text-xs text-slate-600">
                  {item.original_filename}
                </figcaption>
              </figure>
            ))}
          </div>
          <div className="overflow-x-auto border border-slate-200">
            <table
              aria-label={t("analysis.damageTable")}
              className="w-full min-w-[36rem] border-collapse text-left text-sm"
            >
              <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-600">
                <tr>
                  <th className="px-4 py-3" scope="col">
                    {t("analysis.part")}
                  </th>
                  <th className="px-4 py-3" scope="col">
                    {t("analysis.damageType")}
                  </th>
                  <th className="px-4 py-3 text-right" scope="col">
                    {t("analysis.areaPercent")}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 bg-white">
                {analysis.detections.map((detection, index) => (
                  <tr key={`${detection.annotated_evidence.id}-${index}`}>
                    <td className="px-4 py-3 font-semibold text-slate-950">
                      {formatLabel(detection.vehicle_part) ||
                        t("analysis.areaUnknown")}
                    </td>
                    <td className="px-4 py-3 text-slate-700">
                      {formatLabel(detection.damage_type) ||
                        t("analysis.damageUnknown")}
                    </td>
                    <td className="px-4 py-3 text-right font-mono font-semibold text-slate-950">
                      {formatPercent(detection.damage_percentage)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="flex min-h-24 items-center justify-center gap-2 border border-dashed border-slate-300 bg-slate-50 text-sm text-slate-600">
          <Image size={20} />
          {t("analysis.noDamage")}
        </div>
      )}
    </section>
  );
}

export function AiReviewPanel({ claim }: { claim: ClaimDetail }) {
  const { t } = useTranslation();
  const run = claim.latest_analysis_run;
  const conclusion =
    run?.damage_analysis?.copilot_conclusion ??
    (!run ? claim.latest_damage_analysis?.copilot_conclusion : null);
  const review = useWorkflowAiReview(claim.id, run?.id);
  const ready = Boolean(
    run &&
    !run.inputs_changed &&
    ["COMPLETED", "PARTIAL"].includes(run.status) &&
    run.damage_analysis &&
    (!run.analysis_readiness || run.analysis_readiness.status === "READY"),
  );
  const blockedReasons = run?.analysis_readiness?.blocked_reasons ?? [];
  return (
    <Card
      className="rounded-lg border border-slate-200 bg-white shadow-sm"
      id="aiReview"
    >
      <Card.Header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-lg bg-teal-50 text-teal-700 ring-1 ring-teal-100">
            <DataStructured size={20} />
          </div>
          <div>
            <Card.Title className="text-lg text-slate-950">
              {t("claim.stepAiReview")}
            </Card.Title>
            <Card.Description className="text-sm text-slate-500">
              {t("aiReview.description")}
            </Card.Description>
          </div>
        </div>
        {!conclusion ? (
          <Button
            isDisabled={!ready}
            isPending={review.isPending}
            onPress={() => review.mutate()}
            variant="primary"
          >
            {t("aiReview.run")}
          </Button>
        ) : null}
      </Card.Header>
      <Card.Content className="grid gap-5 p-6">
        {review.error ? (
          <Alert status="danger">
            <Alert.Title>{t("aiReview.failed")}</Alert.Title>
            <Alert.Description>
              {review.error instanceof ClaimsApiError
                ? review.error.message
                : t("common.tryAgain")}
            </Alert.Description>
          </Alert>
        ) : null}
        {conclusion ? (
          <AiReviewResult conclusion={conclusion} />
        ) : (
          <div className="grid gap-2 text-sm text-slate-500">
            <p>{ready ? t("aiReview.ready") : t("aiReview.blocked")}</p>
            {!ready && blockedReasons.length ? (
              <ul className="list-disc space-y-1 pl-5 text-xs text-amber-800">
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
            ) : null}
          </div>
        )}
      </Card.Content>
    </Card>
  );
}

function AiReviewResult({ conclusion }: { conclusion: CopilotConclusion }) {
  const { t } = useTranslation();
  const warnings = Array.from(
    new Set([
      ...conclusion.warnings,
      ...(conclusion.structured_review?.warnings ?? []),
    ]),
  );

  return (
    <div className="grid gap-5">
      <div className="grid gap-4 border-b border-slate-100 pb-5 sm:grid-cols-[12rem_minmax(0,1fr)]">
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500">
            {t("aiReview.validity")}
          </p>
          <p className="mt-2 font-mono text-4xl font-semibold text-slate-950">
            {conclusion.validity_percentage ?? "--"}%
          </p>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            {t("aiReview.validityDisclaimer")}
          </p>
        </div>
        <div>
          <div className="flex flex-wrap gap-2">
            <Chip color="warning" variant="soft">
              {conclusion.review_status ?? t("aiReview.reviewRequired")}
            </Chip>
            <Chip
              color={
                conclusion.status === "GENERATED"
                  ? "success"
                  : conclusion.status === "LLM_UNAVAILABLE"
                    ? "danger"
                    : "default"
              }
              variant="soft"
            >
              {conclusion.status === "GENERATED"
                ? t("aiReview.generated")
                : conclusion.status === "LLM_UNAVAILABLE"
                  ? t("aiReview.unavailable")
                  : t("aiReview.fallback")}
            </Chip>
          </div>
          <p className="mt-4 text-sm leading-6 text-slate-700">
            {conclusion.summary}
          </p>
        </div>
      </div>
      {conclusion.status === "LLM_UNAVAILABLE" ? (
        <Alert status="danger">
          <Alert.Title>{t("aiReview.unavailable")}</Alert.Title>
          <Alert.Description>
            {conclusion.failure_reason ?? t("aiReview.failed")}
          </Alert.Description>
        </Alert>
      ) : null}
      {conclusion.structured_review ? (
        <div className="grid gap-3">
          <dl className="divide-y divide-slate-200 border-y border-slate-200">
            {[
              [
                t("aiReview.assessmentInterpretation"),
                conclusion.structured_review.assessment_interpretation,
              ],
              [
                t("aiReview.damagedPartsSummary"),
                conclusion.structured_review.damaged_parts_summary,
              ],
              [
                t("aiReview.documentConsistency"),
                conclusion.structured_review.document_consistency_summary,
              ],
              [
                t("aiReview.recommendedNextStep"),
                conclusion.structured_review.recommended_next_step,
              ],
            ].map(([label, value]) => (
              <div className="grid gap-1 py-3 sm:grid-cols-[13rem_minmax(0,1fr)]" key={label}>
                <dt className="text-xs font-semibold text-slate-600">{label}</dt>
                <dd className="text-sm leading-6 text-slate-800">{value}</dd>
              </div>
            ))}
          </dl>
          {conclusion.structured_review.human_review_required ? (
            <p className="border-l-2 border-amber-500 bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-950">
              {t("aiReview.humanReviewRequired")}
            </p>
          ) : null}
        </div>
      ) : null}
      {warnings.length ? (
        <Alert status="warning">
          <WarningAlt size={18} />
          <Alert.Title>{t("aiReview.warnings")}</Alert.Title>
          <Alert.Description>{warnings.join(" ")}</Alert.Description>
        </Alert>
      ) : null}
      <div>
        <h3 className="text-sm font-semibold text-slate-950">
          {t("aiReview.evidenceReferences")}
        </h3>
        <div className="mt-2 flex flex-wrap gap-2">
          {(conclusion.evidence_references ?? []).map((item) => (
            <Chip key={item.id} size="sm" variant="soft">
              {item.original_filename}
            </Chip>
          ))}
        </div>
      </div>
    </div>
  );
}

const rejectionCategories: CopilotConclusionRejectionCategory[] = [
  "DOCUMENT_INFORMATION_INCOMPLETE",
  "DOCUMENT_INFORMATION_INCORRECT",
  "DAMAGE_ASSESSMENT_ISSUE",
  "DAMAGE_EVIDENCE_ISSUE",
  "MISSING_EVIDENCE",
  "INCORRECT_AI_CONCLUSION",
  "OTHER",
];

export function HumanReviewPanel({ claim }: { claim: ClaimDetail }) {
  const { t } = useTranslation();
  const { session } = useAuth();
  const run = claim.latest_analysis_run;
  const conclusion =
    run?.damage_analysis?.copilot_conclusion ??
    (!run ? claim.latest_damage_analysis?.copilot_conclusion : undefined);
  const submit = useReviewCopilotConclusion(claim.id, conclusion?.id);
  const revert = useRevertCopilotReview(claim.id, conclusion?.id);
  const latest = conclusion?.review_history[0];
  const [mode, setMode] = useState<"APPROVED" | "REJECTED">("APPROVED");
  const [note, setNote] = useState("");
  const [reason, setReason] = useState<CopilotConclusionRejectionCategory | "">(
    "",
  );
  const [revertNote, setRevertNote] = useState("");
  const canReview =
    (session?.user.role === "ADJUSTER" || session?.user.role === "ADMIN") &&
    conclusion &&
    !latest;

  function save(event: FormEvent) {
    event.preventDefault();
    if (!note.trim() || (mode === "REJECTED" && !reason)) return;
    submit.mutate({
      status: mode,
      comment: note.trim(),
      ...(mode === "REJECTED"
        ? { reason_category: reason as CopilotConclusionRejectionCategory }
        : {}),
    });
  }

  return (
    <Card
      className="rounded-lg border border-slate-200 bg-white shadow-sm"
      id="humanReview"
    >
      <Card.Header className="flex items-center gap-3 border-b border-slate-100 px-6 py-5">
        <div className="flex size-10 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700 ring-1 ring-emerald-100">
          <CheckmarkOutline size={20} />
        </div>
        <div>
          <Card.Title className="text-lg text-slate-950">
            {t("claim.stepHumanReview")}
          </Card.Title>
          <Card.Description className="text-sm text-slate-500">
            {t("humanReview.description")}
          </Card.Description>
        </div>
      </Card.Header>
      <Card.Content className="grid gap-5 p-6">
        {!conclusion ? (
          <p className="text-sm text-slate-500">{t("humanReview.blocked")}</p>
        ) : null}
        {canReview ? (
          <form className="grid gap-4" onSubmit={save}>
            <div className="flex gap-2">
              <Button
                onPress={() => setMode("APPROVED")}
                variant={mode === "APPROVED" ? "primary" : "outline"}
              >
                {t("humanReview.approve")}
              </Button>
              <Button
                onPress={() => setMode("REJECTED")}
                variant={mode === "REJECTED" ? "danger" : "outline"}
              >
                {t("humanReview.reject")}
              </Button>
            </div>
            {mode === "REJECTED" ? (
              <label className="grid gap-1 text-sm font-medium text-slate-700">
                {t("humanReview.reason")}
                <select
                  aria-label={t("humanReview.reason")}
                  className="min-h-10 border border-slate-300 bg-white px-3"
                  onChange={(event) =>
                    setReason(
                      event.target.value as CopilotConclusionRejectionCategory,
                    )
                  }
                  value={reason}
                >
                  <option value="">{t("humanReview.selectReason")}</option>
                  {rejectionCategories.map((category) => (
                    <option key={category} value={category}>
                      {t(`humanReview.reasons.${category}`)}
                    </option>
                  ))}
                </select>
              </label>
            ) : null}
            <TextField isRequired>
              <Label>{t("humanReview.note")}</Label>
              <Input
                value={note}
                onChange={(event) => setNote(event.target.value)}
              />
            </TextField>
            <Button
              isDisabled={!note.trim() || (mode === "REJECTED" && !reason)}
              isPending={submit.isPending}
              type="submit"
              variant={mode === "REJECTED" ? "danger" : "primary"}
            >
              {t("humanReview.submit")}
            </Button>
          </form>
        ) : null}
        {latest ? (
          <div className="grid gap-4">
            <ReviewHistory history={conclusion.review_history} />
            {!latest.reverted_at ? (
              <div className="grid gap-3 border-t border-slate-100 pt-4">
                <TextField isRequired>
                  <Label>{t("humanReview.revertNote")}</Label>
                  <Input
                    value={revertNote}
                    onChange={(event) => setRevertNote(event.target.value)}
                  />
                </TextField>
                <Button
                  isDisabled={!revertNote.trim()}
                  isPending={revert.isPending}
                  onPress={() => revert.mutate(revertNote.trim())}
                  variant="outline"
                >
                  <Reset size={17} />
                  {t("humanReview.revert")}
                </Button>
              </div>
            ) : (
              <Alert status="warning">
                <Alert.Title>{t("humanReview.reverted")}</Alert.Title>
                <Alert.Description>
                  {t("humanReview.rerunAfterRevert")}
                </Alert.Description>
              </Alert>
            )}
          </div>
        ) : null}
      </Card.Content>
    </Card>
  );
}

export function CopilotReviewHistory({
  history,
}: {
  history: CopilotConclusionReview[];
}) {
  const { t } = useTranslation();
  if (!history.length) return null;
  return (
    <section className="grid gap-3 border-y border-slate-200 py-5">
      <h2 className="text-sm font-semibold text-slate-950">
        {t("humanReview.history")}
      </h2>
      <ReviewHistory history={history} />
    </section>
  );
}

function ReviewHistory({ history }: { history: CopilotConclusionReview[] }) {
  const { t } = useTranslation();
  return (
    <div className="grid gap-3 border-l-2 border-slate-300 pl-3">
      {history.map((review) => (
        <div
          className="grid gap-1 text-sm"
          key={`${review.conclusion_id}-${review.reviewed_at}`}
        >
          <div className="flex flex-wrap items-center gap-2">
            <Chip
              color={review.status === "APPROVED" ? "success" : "danger"}
              size="sm"
              variant="soft"
            >
              {review.status === "APPROVED"
                ? t("humanReview.approved")
                : t("humanReview.rejected")}
            </Chip>
            {review.reverted_at ? (
              <Chip color="warning" size="sm" variant="soft">
                {t("humanReview.reverted")}
              </Chip>
            ) : null}
            <span className="text-xs text-slate-500">
              {t("humanReview.reviewedBy", {
                reviewer: review.reviewer,
                date: new Date(review.reviewed_at).toLocaleString(),
              })}
            </span>
          </div>
          {review.reason_category ? (
            <p className="text-xs text-slate-600">
              {t("humanReview.reasonValue", {
                reason: t(`humanReview.reasons.${review.reason_category}`),
              })}
            </p>
          ) : null}
          {review.comment ? (
            <p className="text-sm text-slate-700">{review.comment}</p>
          ) : null}
          {review.revert_note ? (
            <p className="text-xs text-amber-800">
              {t("humanReview.revertValue", { note: review.revert_note })}
            </p>
          ) : null}
        </div>
      ))}
    </div>
  );
}

function formatLabel(value: string | null) {
  return value
    ?.replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}
function formatPercent(value: number) {
  return `${Number.isInteger(value) ? value : value.toFixed(1)}%`;
}
