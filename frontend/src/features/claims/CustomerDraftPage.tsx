import { ArrowLeft, CheckmarkOutline } from "@carbon/icons-react";
import { Alert, Button, Chip, Skeleton, toast } from "@heroui/react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate, useParams } from "react-router";

import { ClaimInformationPanel } from "./ClaimInformationPanel";
import { ClaimWorkflowStepper } from "./ClaimWorkflowStepper";
import { EvidencePanel, requiredEvidenceCategories } from "./EvidencePanel";
import { ClaimsApiError } from "./claimsApi";
import { useClaim, useSubmitClaim } from "./useClaims";

export function CustomerDraftPage() {
  const { claimId } = useParams();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: claim, error, isPending } = useClaim(claimId);
  const submit = useSubmitClaim(claimId);
  const [submitError, setSubmitError] = useState("");

  if (isPending)
    return <Skeleton className="mx-auto h-72 max-w-[1440px] rounded-lg" />;
  if (error || !claim || claim.status !== "DRAFT")
    return (
      <Alert status="danger">
        <Alert.Title>{t("claim.unavailable")}</Alert.Title>
      </Alert>
    );

  const uploadedCategories = new Set(
    claim.evidence.map((item) => item.category),
  );
  const ready =
    Boolean(claim.incident) &&
    requiredEvidenceCategories.every((category) =>
      uploadedCategories.has(category),
    );

  async function submitDraft() {
    setSubmitError("");
    try {
      await submit.mutateAsync();
      toast.success(t("myClaims.submitSuccess"));
      navigate("/my-claims", { replace: true });
    } catch (caught) {
      setSubmitError(
        caught instanceof ClaimsApiError
          ? caught.message
          : t("myClaims.submitFailed"),
      );
    }
  }

  return (
    <div className="mx-auto grid max-w-[1440px] gap-6 py-2">
      <Link
        className="flex w-fit items-center gap-2 text-sm font-semibold text-blue-700"
        to="/my-claims"
      >
        <ArrowLeft size={18} />
        {t("myClaims.title")}
      </Link>
      <header className="flex flex-wrap items-end justify-between gap-4 border-b border-slate-200 pb-5">
        <div>
          <p className="text-sm font-semibold text-slate-500">
            {t("claim.intake")}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">
            {t("claim.claimNumber", { id: claim.id })}
          </h1>
        </div>
        <Chip color="default" variant="soft">
          {t("claim.status.DRAFT")}
        </Chip>
      </header>
      <ClaimWorkflowStepper
        current={claim.incident ? "evidence" : "information"}
        maxSteps={2}
        states={{
          information: claim.incident ? "completed" : "current",
          evidence: claim.incident ? "current" : "blocked",
        }}
      />
      <ClaimInformationPanel claim={claim} />
      <EvidencePanel claimId={claim.id} evidence={claim.evidence} />
      <div className="flex flex-wrap items-center justify-between gap-4 border-t border-slate-200 pt-5">
        <p className="text-sm text-slate-600">
          {t("myClaims.evidenceCount", {
            count: requiredEvidenceCategories.filter((category) =>
              uploadedCategories.has(category),
            ).length,
            total: requiredEvidenceCategories.length,
          })}
        </p>
        <Button
          isDisabled={!ready}
          isPending={submit.isPending}
          onPress={submitDraft}
          variant="primary"
        >
          <CheckmarkOutline size={18} />
          {t("myClaims.submit")}
        </Button>
      </div>
      {submitError ? (
        <Alert status="danger">
          <Alert.Title>{t("myClaims.submitFailed")}</Alert.Title>
          <Alert.Description>{submitError}</Alert.Description>
        </Alert>
      ) : null}
    </div>
  );
}
