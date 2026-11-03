import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it } from "vitest";
import i18n from "../../i18n";
import { AuthProvider } from "../auth/AuthProvider";
import { AiReviewPanel, AnalysisPanel } from "./WorkflowPanels";
import { vehiclePartLabels } from "./damagePresentation";
import type { ClaimDetail, DamageAnalysis } from "./types";

const damage: DamageAnalysis = {
  id: "DA-000001",
  assessment: "MANUAL_INSPECTION_REQUIRED",
  warning: null,
  detections: [],
  model_output: {
    adapter_name: "local",
    part_identities: ["fender", "front_bumper", "hood", "windshield"],
    record: {
      source_evidence_ids: [],
      annotated_evidence_ids: [],
      parts: ["Fender", "Front-Bumper", "Hood", "Windshield"].map((part) => ({
        part,
        main_damage: "dent",
        damage_percent: 32.5,
        damage_types: [{ type: "dent", percent: 32.5 }],
      })),
    },
    warnings: [],
  },
  rules: null,
  reference_price_status: "NOT_REQUESTED",
  reference_prices: [],
  copilot_conclusion: {
    id: 1,
    status: "GENERATED",
    recommendation: "MANUAL_ADJUSTER_REVIEW",
    summary: "REPAIR_LIKELY",
    fallback_summary: null,
    failure_reason: null,
    provider_model: null,
    findings: [],
    warnings: ["MANUAL_INSPECTION_REQUIRED"],
    reference_prices: [],
    review_history: [],
    structured_review: {
      summary: "Assessment: REPAIR_LIKELY.",
      assessment_interpretation: "REPLACEMENT_LIKELY",
      damaged_parts_summary: "Damage requires review.",
      document_consistency_summary: "Confirmed documents match.",
      recommended_next_step: "MANUAL_ADJUSTER_REVIEW",
      warnings: [],
      human_review_required: true,
      price_recommendation: {
        recommendation: "MANUAL_REVIEW",
        rationale: "Pricing: MANUAL_INSPECTION_REQUIRED.",
      },
    },
  },
  created_at: "2026-01-01T00:00:00Z",
};
const claim: ClaimDetail = {
  id: "CLM-000001",
  claimant_name: "Mai Nguyen",
  vehicle: {
    make: "Toyota",
    model: "Vios",
    year: 2024,
    license_plate: null,
    vin: null,
  },
  status: "REVIEW_REQUIRED",
  created_at: damage.created_at,
  updated_at: damage.created_at,
  evidence: [],
  latest_damage_analysis: damage,
  latest_analysis_run: {
    id: 1,
    status: "COMPLETED",
    damage_status: "COMPLETED",
    damage_analysis: damage,
    document_analyses: [],
    failure_reason: null,
    created_at: damage.created_at,
    started_at: damage.created_at,
    completed_at: damage.created_at,
  },
};

function renderPanels(targetClaim = claim) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <AuthProvider>
        <AnalysisPanel claim={targetClaim} />
        <AiReviewPanel claim={targetClaim} />
      </AuthProvider>
    </QueryClientProvider>,
  );
}

it("updates part names and table search when the selected language changes", async () => {
  const user = userEvent.setup();
  renderPanels();
  expect(screen.getByRole("cell", { name: "Fender" })).toBeVisible();
  await act(() => i18n.changeLanguage("vi"));
  for (const part of [
    vehiclePartLabels.fender.vi,
    "Cản trước",
    "Nắp ca-pô",
    "Kính chắn gió",
  ]) {
    expect(screen.getByRole("cell", { name: part })).toBeVisible();
  }
  await user.type(
    screen.getByRole("textbox", { name: i18n.t("analysis.searchFindings") }),
    "Cản trước",
  );
  expect(screen.getByRole("cell", { name: "Cản trước" })).toBeVisible();
  expect(
    screen.queryByRole("cell", { name: vehiclePartLabels.fender.vi }),
  ).not.toBeInTheDocument();
  await user.clear(
    screen.getByRole("textbox", { name: i18n.t("analysis.searchFindings") }),
  );
  await act(() => i18n.changeLanguage("en"));
  expect(screen.getByRole("cell", { name: "Front Bumper" })).toBeVisible();
  expect(damage.model_output!.record.parts[1].part).toBe("Front-Bumper");
});

it.each(["model", "legacy"])(
  "translates all seven %s damage types and preserves the selected filter across language changes",
  async (source) => {
    const user = userEvent.setup();
    const types = [
      "corrosion",
      "crack",
      "dent",
      "glass shatter",
      "lamp broken",
      "scratch",
      "tire flat",
    ];
    const localized = [
      "Ăn mòn / Rỉ sét",
      "Nứt",
      "Móp / Lõm",
      "Vỡ kính",
      "Vỡ đèn",
      "Trầy xước",
      "Xẹp lốp",
    ];
    const analysis: DamageAnalysis = {
      ...damage,
      model_output: {
        ...damage.model_output!,
        annotated_evidence: [],
        record: {
          source_evidence_ids: [],
          annotated_evidence_ids: [],
          parts:
            source === "model"
              ? types.map((type) => ({
                  part: "Hood",
                  main_damage: type,
                  damage_percent: 32.5,
                  damage_types: [{ type, percent: 32.5 }],
                }))
              : [],
        },
      },
      detections:
        source === "legacy"
          ? types.map((type, index) => ({
              vehicle_part: "Hood",
              damage_type: type,
              damage_percentage: 32.5,
              confidence: 1,
              status: "DETECTED",
              annotated_evidence: {
                id: index + 1,
                category: "VEHICLE_DAMAGE_IMAGE",
                original_filename: "damage.jpg",
                content_type: "image/jpeg",
                content_url: "/image",
                file_size: 1,
                uploaded_at: damage.created_at,
              },
            }))
          : [],
    };
    renderPanels({
      ...claim,
      latest_damage_analysis: analysis,
      latest_analysis_run: {
        ...claim.latest_analysis_run!,
        damage_analysis: analysis,
      },
    });
    const filter = screen.getByRole("combobox", {
      name: i18n.t("analysis.damageType"),
    });
    await user.selectOptions(filter, "glass_shatter");
    expect(screen.getByRole("cell", { name: "Glass Shatter" })).toBeVisible();
    await act(() => i18n.changeLanguage("vi"));
    expect(filter).toHaveValue("glass_shatter");
    expect(screen.getByRole("cell", { name: "Vỡ kính" })).toBeVisible();
    expect(
      screen.queryByRole("cell", { name: "Trầy xước" }),
    ).not.toBeInTheDocument();
    await user.selectOptions(filter, "ALL");
    for (const label of localized) {
      expect(screen.getByRole("cell", { name: label })).toBeVisible();
      expect(within(filter).getByRole("option", { name: label })).toBeVisible();
    }
    const search = screen.getByRole("textbox", {
      name: i18n.t("analysis.searchFindings"),
    });
    await user.type(search, "Xẹp lốp");
    expect(screen.getByRole("cell", { name: "Xẹp lốp" })).toBeVisible();
    expect(
      screen.queryByRole("cell", { name: "Vỡ kính" }),
    ).not.toBeInTheDocument();
    await user.clear(search);
    await user.selectOptions(filter, "glass_shatter");
    await act(() => i18n.changeLanguage("en"));
    expect(filter).toHaveValue("glass_shatter");
    expect(screen.getByRole("cell", { name: "Glass Shatter" })).toBeVisible();
    expect(types[3]).toBe("glass shatter");
  },
);

it.each(["en", "vi"])(
  "hides technical assessment codes throughout the %s AI review",
  async (language) => {
    await i18n.changeLanguage(language);
    const { container } = renderPanels();
    const review = container.querySelector<HTMLElement>("#aiReview")!;
    expect(review.textContent).not.toMatch(
      /REPAIR_LIKELY|REPLACEMENT_LIKELY|MANUAL_INSPECTION_REQUIRED|MANUAL_ADJUSTER_REVIEW/,
    );
    expect(
      within(review).getByText(
        `Assessment: ${i18n.t("analysis.assessment.REPAIR_LIKELY")}.`,
      ),
    ).toBeVisible();
    expect(
      within(review).getByText(
        i18n.t("analysis.assessment.REPLACEMENT_LIKELY"),
      ),
    ).toBeVisible();
    expect(
      within(review).getByText(
        `Pricing: ${i18n.t("analysis.assessment.MANUAL_INSPECTION_REQUIRED")}.`,
      ),
    ).toBeVisible();
    expect(damage.copilot_conclusion!.structured_review!.summary).toBe(
      "Assessment: REPAIR_LIKELY.",
    );
  },
);
