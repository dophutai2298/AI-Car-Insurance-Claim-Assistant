import { ArrowLeft, Document, TrashCan } from "@carbon/icons-react";
import { Alert, Button, Chip, Modal, Skeleton } from "@heroui/react";
import { useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";

import { useAuth } from "../auth/AuthProvider";
import { ClaimInformationPanel } from "./ClaimInformationPanel";
import {
  ClaimWorkflowStepper,
  claimWorkflowForClaim,
  type ClaimStepId,
} from "./ClaimWorkflowStepper";
import { ClaimWorkflowTabs } from "./ClaimWorkflowTabs";
import { EvidencePanel } from "./EvidencePanel";
import {
  AiReviewPanel,
  AnalysisPanel,
  CopilotReviewHistory,
  HumanReviewPanel,
} from "./WorkflowPanels";
import { statusTone } from "./statusPresentation";
import { ClaimsApiError } from "./claimsApi";
import { useClaim, useDeleteClaim } from "./useClaims";

export function ClaimDetailPage() {
  const { claimId } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { session } = useAuth();
  const { data: claim, error, isPending } = useClaim(claimId);
  const remove = useDeleteClaim(claimId);
  const [isDeleteOpen, setIsDeleteOpen] = useState(false);
  const [deleteError, setDeleteError] = useState("");
  const [view, setView] = useState<{
    claimId: string;
    mode: "page" | "tabs";
    step: ClaimStepId;
  } | null>(null);

  if (isPending)
    return (
      <div className="mx-auto grid max-w-[1440px] gap-6 py-2">
        <Skeleton className="h-10 w-40 rounded-lg" />
        <Skeleton className="h-72 rounded-lg" />
      </div>
    );
  if (error || !claim)
    return (
      <div className="mx-auto max-w-[1440px] py-2">
        <Alert status="danger">
          <Alert.Title>{t("claim.unavailable")}</Alert.Title>
          <Alert.Description>{t("claim.loadFailed")}</Alert.Description>
        </Alert>
        <Link
          className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-blue-700"
          to="/claims"
        >
          <ArrowLeft size={18} />
          {t("claim.backToClaims")}
        </Link>
      </div>
    );

  const workflow = claimWorkflowForClaim(claim);
  const analysisLocked = ["PENDING", "PROCESSING"].includes(
    claim.latest_analysis_run?.status ?? "",
  );
  const currentConclusion =
    claim.latest_analysis_run?.damage_analysis?.copilot_conclusion ??
    (!claim.latest_analysis_run
      ? claim.latest_damage_analysis?.copilot_conclusion
      : undefined);
  const reviewed = currentConclusion?.review_history[0];
  const evidenceLocked =
    analysisLocked || Boolean(reviewed && !reviewed.reverted_at);
  const canDelete = session?.user.role === "ADMIN";
  const currentClaimId = claim.id;
  const mode = view?.claimId === claim.id ? view.mode : "page";
  const selectedStep = view?.claimId === claim.id ? view.step : workflow.current;
  const panels: { id: ClaimStepId; content: ReactNode }[] = [
    { id: "information", content: <ClaimInformationPanel claim={claim} /> },
    {
      id: "evidence",
      content: (
        <EvidencePanel
          claimId={claim.id}
          evidence={claim.evidence ?? []}
          locked={evidenceLocked}
        />
      ),
    },
    { id: "analysis", content: <AnalysisPanel claim={claim} /> },
    { id: "aiReview", content: <AiReviewPanel claim={claim} /> },
    {
      id: "humanReview",
      content: (
        <div className="grid gap-6">
          <HumanReviewPanel claim={claim} />
          <CopilotReviewHistory history={claim.copilot_review_history ?? []} />
        </div>
      ),
    },
  ];

  async function confirmDelete() {
    setDeleteError("");
    try {
      await remove.mutateAsync();
      navigate("/claims", { replace: true });
    } catch (caught) {
      setDeleteError(
        caught instanceof ClaimsApiError
          ? caught.message
          : t("claim.deleteFailed"),
      );
    }
  }

  function navigateToStep(step: ClaimStepId) {
    setView({ claimId: currentClaimId, mode, step });
    if (mode === "page") {
      document
        .getElementById(step)
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  return (
    <div className="mx-auto grid max-w-[1440px] gap-6 py-2">
      <Link
        className="flex w-fit items-center gap-2 text-sm font-semibold text-blue-700"
        to="/claims"
      >
        <ArrowLeft size={18} />
        {t("claim.backToClaims")}
      </Link>
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-500">
            {t("claim.case")}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">
            {t("claim.claimNumber", { id: claim.id })}
          </h1>
          <p className="mt-2 text-sm text-slate-600">
            {t("claim.createdFor", { name: claim.claimant_name })}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {canDelete ? (
            <Button
              className="text-white"
              onPress={() => setIsDeleteOpen(true)}
              variant="danger"
            >
              <TrashCan size={17} />
              {t("claim.deleteClaim")}
            </Button>
          ) : null}
          <Chip color={statusTone[claim.status]} variant="soft">
            {t(`claim.status.${claim.status}`)}
          </Chip>
        </div>
      </header>
      {deleteError ? (
        <Alert status="danger">
          <Alert.Title>{t("claim.deleteFailed")}</Alert.Title>
          <Alert.Description>{deleteError}</Alert.Description>
        </Alert>
      ) : null}
      <div className="flex justify-end">
        <div
          aria-label={t("claim.layoutMode")}
          className="inline-flex gap-1 rounded-lg border border-slate-200 bg-white p-1"
          role="group"
        >
          <Button
            aria-pressed={mode === "page"}
            onPress={() =>
              setView({ claimId: claim.id, mode: "page", step: selectedStep })
            }
            size="sm"
            variant={mode === "page" ? "primary" : "ghost"}
          >
            {t("claim.singlePage")}
          </Button>
          <Button
            aria-pressed={mode === "tabs"}
            onPress={() =>
              setView({ claimId: claim.id, mode: "tabs", step: selectedStep })
            }
            size="sm"
            variant={mode === "tabs" ? "primary" : "ghost"}
          >
            {t("claim.tabLayout")}
          </Button>
        </div>
      </div>
      {mode === "page" ? (
        <ClaimWorkflowStepper
          current={workflow.current}
          onNavigate={navigateToStep}
          states={workflow.states}
        />
      ) : (
        <ClaimWorkflowTabs
          onSelect={navigateToStep}
          selected={selectedStep}
          states={workflow.states}
        />
      )}
      {panels.map(({ id, content }) => (
        <div
          aria-labelledby={mode === "tabs" ? `claim-tab-${id}` : undefined}
          hidden={mode === "tabs" && selectedStep !== id}
          id={mode === "tabs" ? `claim-panel-${id}` : undefined}
          key={id}
          role={mode === "tabs" ? "tabpanel" : undefined}
          tabIndex={mode === "tabs" ? 0 : undefined}
        >
          {content}
        </div>
      ))}
      <Alert status="warning">
        <Document size={18} />
        <Alert.Title>{t("claim.safetyTitle")}</Alert.Title>
        <Alert.Description>{t("claim.safetyDescription")}</Alert.Description>
      </Alert>
      <Modal>
        <Modal.Backdrop
          isOpen={isDeleteOpen}
          onOpenChange={(isOpen) => {
            if (!isOpen && !remove.isPending) setIsDeleteOpen(false);
          }}
        >
          <Modal.Container>
            <Modal.Dialog className="sm:max-w-md">
              <Modal.Header>
                <Modal.Heading>{t("claim.deleteClaimTitle")}</Modal.Heading>
              </Modal.Header>
              <Modal.Body>
                <p className="text-sm text-slate-600">
                  {t("claim.deleteClaimDescription", { id: claim.id })}
                </p>
              </Modal.Body>
              <Modal.Footer>
                <Button
                  isDisabled={remove.isPending}
                  onPress={() => setIsDeleteOpen(false)}
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
                  {t("claim.deleteClaim")}
                </Button>
              </Modal.Footer>
            </Modal.Dialog>
          </Modal.Container>
        </Modal.Backdrop>
      </Modal>
    </div>
  );
}
