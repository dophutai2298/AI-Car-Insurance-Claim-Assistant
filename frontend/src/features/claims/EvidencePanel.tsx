import {
  Add,
  CheckmarkOutline,
  Document,
  Image,
  TrashCan,
  WarningAlt,
} from "@carbon/icons-react";
import {
  Alert,
  Button,
  Card,
  Chip,
  Input,
  Label,
  Modal,
  TextField,
} from "@heroui/react";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthProvider";
import { ClaimsApiError, getEvidenceContent } from "./claimsApi";
import { useDeleteEvidence, useUploadEvidence } from "./useClaims";
import type { EvidenceCategory, EvidenceItem } from "./types";

export const requiredEvidenceCategories: EvidenceCategory[] = [
  "VEHICLE_DAMAGE_IMAGE",
  "ID_CARD",
  "INSURANCE_POLICY",
  "VEHICLE_REGISTRATION",
  "DRIVER_LICENSE",
];

export function EvidencePanel({
  claimId,
  evidence,
  locked = false,
}: {
  claimId: string;
  evidence: EvidenceItem[];
  locked?: boolean;
}) {
  const { t } = useTranslation();
  const upload = useUploadEvidence(claimId);
  const remove = useDeleteEvidence(claimId);
  const [error, setError] = useState("");
  const [otherLabel, setOtherLabel] = useState("");
  const [otherFiles, setOtherFiles] = useState<File[]>([]);
  const [deleteTarget, setDeleteTarget] = useState<EvidenceItem | null>(null);

  async function uploadFiles(
    category: EvidenceCategory,
    files: File[],
    label?: string,
  ) {
    if (!files.length) return;
    setError("");
    try {
      await upload.mutateAsync({
        items: files.map((file) => ({ file, category })),
        otherDocumentLabel: label,
      });
      if (category === "OTHER_DOCUMENT") {
        setOtherLabel("");
        setOtherFiles([]);
      }
    } catch (caught) {
      setError(
        caught instanceof ClaimsApiError
          ? caught.message
          : t("evidence.uploadFailed"),
      );
    }
  }

  async function confirmDelete() {
    if (!deleteTarget) return;
    setError("");
    try {
      await remove.mutateAsync(deleteTarget.id);
      setDeleteTarget(null);
    } catch (caught) {
      setError(
        caught instanceof ClaimsApiError
          ? caught.message
          : t("evidence.deleteFailed"),
      );
    }
  }

  const otherGroups = groupOtherDocuments(evidence);

  return (
    <Card
      className="rounded-lg border border-slate-200 bg-white shadow-sm"
      id="evidence"
    >
      <Card.Header className="flex items-start justify-between gap-4 border-b border-slate-100 px-6 py-5">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700 ring-1 ring-blue-100">
            <Document size={20} />
          </div>

          <div>
            <Card.Title className="text-lg text-slate-950">
              {t("claim.stepEvidence")}
            </Card.Title>
            <Card.Description className="text-sm text-slate-500">
              {t("evidence.description")}
            </Card.Description>
          </div>
        </div>
      </Card.Header>
      <Card.Content className="grid gap-5 p-6">
        {error ? (
          <Alert status="danger">
            <Alert.Title>{t("evidence.uploadFailed")}</Alert.Title>
            <Alert.Description>{error}</Alert.Description>
          </Alert>
        ) : null}
        <div className="grid gap-4 xl:grid-cols-2">
          {requiredEvidenceCategories.map((category) => (
            <CategorySection
              category={category}
              evidence={evidence.filter((item) => item.category === category)}
              isPending={upload.isPending}
              key={category}
              locked={locked}
              onRemove={setDeleteTarget}
              onUpload={(files) => uploadFiles(category, files)}
            />
          ))}
        </div>
        <section className="grid gap-4 border-t border-slate-200 pt-5">
          <div>
            <h3 className="text-sm font-semibold text-slate-950">
              {t("evidence.otherDocuments")}
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              {t("evidence.otherDescription")}
            </p>
          </div>
          {[...otherGroups.entries()].map(([groupId, items]) => (
            <div className="border border-slate-200 p-4" key={groupId}>
              <p className="text-sm font-semibold text-slate-950">
                {items[0].group_label}
              </p>
              <EvidenceFiles
                evidence={items}
                locked={locked}
                onRemove={setDeleteTarget}
              />
            </div>
          ))}
          {!locked ? (
            <div className="grid gap-3 border border-dashed border-slate-300 bg-slate-50 p-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_auto] md:items-end">
              <TextField isRequired>
                <Label>{t("evidence.documentName")}</Label>
                <Input
                  value={otherLabel}
                  onChange={(event) => setOtherLabel(event.target.value)}
                />
              </TextField>
              <label className="grid gap-1 text-sm font-medium text-slate-700">
                {t("evidence.files")}
                <input
                  aria-label={t("evidence.otherFiles")}
                  className="min-h-10 border border-slate-300 bg-white px-3 py-2 text-sm"
                  multiple
                  onChange={(event) =>
                    setOtherFiles(Array.from(event.target.files ?? []))
                  }
                  type="file"
                />
              </label>
              <Button
                isDisabled={!otherLabel.trim() || !otherFiles.length}
                isPending={upload.isPending}
                onPress={() =>
                  uploadFiles("OTHER_DOCUMENT", otherFiles, otherLabel.trim())
                }
                variant="outline"
              >
                <Add size={17} />
                {t("evidence.addOther")}
              </Button>
            </div>
          ) : null}
        </section>
      </Card.Content>
      <Modal>
        <Modal.Backdrop
          isOpen={deleteTarget !== null}
          onOpenChange={(isOpen) => {
            if (!isOpen && !remove.isPending) setDeleteTarget(null);
          }}
        >
          <Modal.Container>
            <Modal.Dialog className="sm:max-w-md">
              <Modal.Header>
                <Modal.Heading>
                  {t("evidence.confirmDeleteTitle")}
                </Modal.Heading>
              </Modal.Header>
              <Modal.Body>
                <p className="text-sm text-slate-600">
                  {t("evidence.confirmDeleteDescription", {
                    filename: deleteTarget?.original_filename ?? "",
                  })}
                </p>
              </Modal.Body>
              <Modal.Footer>
                <Button
                  isDisabled={remove.isPending}
                  onPress={() => setDeleteTarget(null)}
                  variant="outline"
                >
                  {t("common.cancel")}
                </Button>
                <Button
                  className="bg-red-600 text-white hover:bg-red-700"
                  isPending={remove.isPending}
                  onPress={confirmDelete}
                >
                  <TrashCan size={17} />
                  {t("evidence.deleteAction")}
                </Button>
              </Modal.Footer>
            </Modal.Dialog>
          </Modal.Container>
        </Modal.Backdrop>
      </Modal>
    </Card>
  );
}

function CategorySection({
  category,
  evidence,
  locked,
  isPending,
  onUpload,
  onRemove,
}: {
  category: EvidenceCategory;
  evidence: EvidenceItem[];
  locked: boolean;
  isPending: boolean;
  onUpload: (files: File[]) => void;
  onRemove: (item: EvidenceItem) => void;
}) {
  const { t } = useTranslation();
  const input = useRef<HTMLInputElement>(null);
  const complete = evidence.length > 0;
  const analysisRequired = evidence.some((item) => item.analysis_required);
  return (
    <section
      className={`grid content-start gap-3 border p-4 ${complete ? "border-emerald-200 bg-emerald-50/40" : "border-amber-200 bg-amber-50/40"}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-950">
            {t(`evidence.categories.${category}`)}
          </h3>
          <p className="mt-1 text-xs text-slate-500">
            {t(`evidence.hints.${category}`)}
          </p>
        </div>
        <Chip
          color={!complete || analysisRequired ? "warning" : "success"}
          size="sm"
          variant="soft"
        >
          {complete && !analysisRequired ? (
            <CheckmarkOutline size={14} />
          ) : (
            <WarningAlt size={14} />
          )}
          {!complete
            ? t("evidence.required")
            : analysisRequired
              ? t("evidence.analysisRequired")
              : t("evidence.uploaded")}
        </Chip>
      </div>
      <EvidenceFiles evidence={evidence} locked={locked} onRemove={onRemove} />
      {!locked ? (
        <>
          <input
            aria-label={t("evidence.selectFor", {
              category: t(`evidence.categories.${category}`),
            })}
            className="sr-only"
            multiple
            onChange={(event) => {
              onUpload(Array.from(event.target.files ?? []));
              event.target.value = "";
            }}
            ref={input}
            type="file"
          />
          <Button
            isPending={isPending}
            onPress={() => input.current?.click()}
            size="sm"
            variant="outline"
          >
            <Add size={16} />
            {complete ? t("evidence.addMore") : t("evidence.selectFiles")}
          </Button>
        </>
      ) : null}
    </section>
  );
}

function EvidenceFiles({
  evidence,
  locked,
  onRemove,
}: {
  evidence: EvidenceItem[];
  locked: boolean;
  onRemove: (item: EvidenceItem) => void;
}) {
  const { t } = useTranslation();
  if (!evidence.length) return null;
  return (
    <div className="grid gap-2">
      {evidence.map((item) => (
        <div
          className="flex min-w-0 items-center gap-3 border border-slate-200 bg-white p-2"
          key={item.id}
        >
          <div className="flex size-20 shrink-0 items-center justify-center overflow-hidden rounded bg-slate-100">
            {item.content_type?.startsWith("image/") ? (
              <EvidenceImagePreview
                className="size-20 object-cover"
                item={item}
              />
            ) : (
              <Document className="text-slate-500" size={24} />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-slate-950">
              {item.original_filename}
            </p>
            <p className="text-xs text-slate-500">
              {formatFileSize(item.file_size)}
            </p>
            {item.analysis_required ? (
              <p className="mt-1 text-xs font-medium text-amber-700">
                {t("evidence.analysisRequired")}
              </p>
            ) : null}
          </div>
          {!locked ? (
            <Button
              aria-label={t("evidence.removeFile", {
                filename: item.original_filename,
              })}
              isIconOnly
              onPress={() => onRemove(item)}
              size="sm"
              variant="ghost"
            >
              <TrashCan size={17} />
            </Button>
          ) : null}
        </div>
      ))}
    </div>
  );
}

export function EvidenceImagePreview({
  item,
  className = "h-32 w-full object-cover",
}: {
  item: EvidenceItem;
  className?: string;
}) {
  const { session } = useAuth();
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  useEffect(() => {
    let objectUrl: string | null = null;
    let active = true;
    getEvidenceContent(item.content_url, session!.access_token)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        if (active) setPreviewUrl(objectUrl);
      })
      .catch(() => active && setPreviewUrl(null));
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [item.content_url, session]);
  return previewUrl ? (
    <a href={previewUrl} rel="noopener noreferrer" target="_blank">
      <img
        alt={item.original_filename}
        className={className}
        src={previewUrl}
      />
    </a>
  ) : (
    <Image className="text-slate-500" size={28} />
  );
}

function formatFileSize(size: number) {
  return size < 1024 ? `${size} B` : `${Math.round(size / 1024)} KB`;
}

function groupOtherDocuments(evidence: EvidenceItem[]) {
  const groups = new Map<number, EvidenceItem[]>();
  for (const item of evidence.filter(
    (candidate) => candidate.category === "OTHER_DOCUMENT",
  )) {
    const key = item.group_id ?? item.id;
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }
  return groups;
}
