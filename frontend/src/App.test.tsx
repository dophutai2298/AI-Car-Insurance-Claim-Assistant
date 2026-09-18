import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { expect, test, vi } from "vitest";

import { AppRoutes } from "./App";
import { AuthProvider } from "./features/auth/AuthProvider";
import type { AssessmentRuleConfiguration } from "./features/admin/types";
import type {
  ClaimDetail,
  EvidenceCategory,
  EvidenceItem,
} from "./features/claims/types";

const adminSession = {
  access_token: "admin-token",
  token_type: "bearer",
  user: { email: "admin@example.com", full_name: "Demo Admin", role: "ADMIN" },
};

const adjusterSession = {
  access_token: "adjuster-token",
  token_type: "bearer",
  user: {
    email: "adjuster@example.com",
    full_name: "Demo Adjuster",
    role: "ADJUSTER",
  },
};

function renderRoute(path: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

test("unauthenticated user is redirected to login", async () => {
  renderRoute("/dashboard");

  expect(
    await screen.findByRole("heading", { name: /sign in to claim assistant/i }),
  ).toBeVisible();
});

test("admin can log in and land on dashboard with admin navigation", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(adminSession), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
  const user = userEvent.setup();
  renderRoute("/login");

  await user.type(screen.getByLabelText(/email/i), "admin@example.com");
  await user.type(screen.getByLabelText(/password/i), "Admin123!");
  await user.click(screen.getByRole("button", { name: /sign in/i }));

  expect(
    await screen.findByRole("heading", { name: /claim review workspace/i }),
  ).toBeVisible();
  expect(screen.getByRole("link", { name: /admin config/i })).toBeVisible();
  expect(sessionStorage.getItem("claim-assistant-session")).toContain(
    "admin-token",
  );
});

test("adjuster cannot open the admin route", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(adjusterSession.user), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
  sessionStorage.setItem(
    "claim-assistant-session",
    JSON.stringify(adjusterSession),
  );
  renderRoute("/admin");

  expect(
    await screen.findByRole("heading", { name: /access restricted/i }),
  ).toBeVisible();
  expect(
    screen.queryByRole("link", { name: /admin config/i }),
  ).not.toBeInTheDocument();
});

test("server role overrides an admin role fabricated in browser storage", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(adjusterSession.user), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
  sessionStorage.setItem(
    "claim-assistant-session",
    JSON.stringify({ ...adjusterSession, user: adminSession.user }),
  );
  renderRoute("/admin");

  expect(
    await screen.findByRole("heading", { name: /access restricted/i }),
  ).toBeVisible();
});

test("invalid credentials display the safe API error", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify({ detail: "Invalid email or password" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    }),
  );
  const user = userEvent.setup();
  renderRoute("/login");

  await user.type(screen.getByLabelText(/email/i), "admin@example.com");
  await user.type(screen.getByLabelText(/password/i), "incorrect");
  await user.click(screen.getByRole("button", { name: /sign in/i }));

  expect(await screen.findByText("Invalid email or password")).toBeVisible();
});

test("claims route renders the dedicated claim table", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    if (String(input).endsWith("/api/auth/me"))
      return new Response(JSON.stringify(adjusterSession.user));
    return new Response(
      JSON.stringify([
        {
          id: "CLM-000071",
          claimant_name: "Mai Nguyen",
          vehicle_summary: "2022 Toyota Camry",
          status: "DRAFT",
          updated_at: "2026-09-08T00:00:00Z",
        },
      ]),
    );
  });
  sessionStorage.setItem(
    "claim-assistant-session",
    JSON.stringify(adjusterSession),
  );
  renderRoute("/claims");

  expect(
    await screen.findByRole("heading", { name: /claim cases/i }),
  ).toBeVisible();
  expect(await screen.findByRole("table")).toBeVisible();
  expect(screen.getByRole("link", { name: /clm-000071/i })).toBeVisible();
});

test("adjuster can create a claim and open its detail", async () => {
  const createdClaim = {
    id: "CLM-000042",
    claimant_name: "Mai Nguyen",
    vehicle: {
      make: "Toyota",
      model: "Camry",
      year: 2022,
      license_plate: "51H-123.45",
      vin: "4T1G11AKXNU123456",
    },
    status: "DRAFT",
    created_at: "2026-09-08T00:00:00Z",
    updated_at: "2026-09-08T00:00:00Z",
  };
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    if (String(input).endsWith("/api/auth/me")) {
      return new Response(JSON.stringify(adjusterSession.user), {
        status: 200,
      });
    }
    if (String(input).endsWith("/api/claims") && init?.method === "POST") {
      return new Response(JSON.stringify(createdClaim), { status: 201 });
    }
    if (String(input).endsWith("/api/vehicle-makes")) {
      return new Response(
        JSON.stringify([{ id: 1, name: "Toyota", is_active: true }]),
        { status: 200 },
      );
    }
    if (String(input).endsWith("/api/claims/CLM-000042")) {
      return new Response(JSON.stringify(createdClaim), { status: 200 });
    }
    return new Response(JSON.stringify([]), { status: 200 });
  });
  sessionStorage.setItem(
    "claim-assistant-session",
    JSON.stringify(adjusterSession),
  );
  const user = userEvent.setup();
  renderRoute("/claims/new");

  expect(
    await screen.findByRole("navigation", { name: /primary navigation/i }),
  ).toBeVisible();
  expect(
    within(
      screen.getByRole("navigation", { name: /primary navigation/i }),
    ).getByRole("link", { name: /^claims$/i }),
  ).toBeVisible();
  await user.type(await screen.findByLabelText(/claimant name/i), "Mai Nguyen");
  await user.click(await screen.findByLabelText(/vehicle make/i));
  await user.click(await screen.findByRole("option", { name: "Toyota" }));
  await user.type(screen.getByLabelText(/model/i), "Camry");
  await user.type(screen.getByLabelText(/year/i), "2022");
  await user.type(
    screen.getByLabelText(/incident date and time/i),
    "2026-09-09T08:30",
  );
  await user.type(screen.getByLabelText(/incident location/i), "District 1");
  await user.type(
    screen.getByLabelText(/incident description/i),
    "Rear impact.",
  );
  await user.click(screen.getByRole("button", { name: /create claim/i }));

  expect(
    await screen.findByRole("heading", { name: /claim clm-000042/i }),
  ).toBeVisible();
  expect(screen.getByText("Toyota Camry")).toBeVisible();
  expect(
    screen.getByRole("navigation", { name: /primary navigation/i }),
  ).toBeVisible();
});

test("claim information uses a vehicle-make autocomplete and persists the selected language", async () => {
  const createdClaim = {
    id: "CLM-000043",
    claimant_name: "Mai Nguyen",
    vehicle: {
      make: "Toyota",
      model: "Camry",
      year: 2022,
      license_plate: null,
      vin: null,
    },
    status: "DRAFT",
    created_at: "2026-09-08T00:00:00Z",
    updated_at: "2026-09-08T00:00:00Z",
  };
  let submittedMake = "";
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    if (String(input).endsWith("/api/auth/me"))
      return new Response(JSON.stringify(adjusterSession.user));
    if (String(input).endsWith("/api/vehicle-makes")) {
      return new Response(
        JSON.stringify([
          { id: 1, name: "Toyota", is_active: true },
          { id: 2, name: "VinFast", is_active: true },
        ]),
      );
    }
    if (String(input).endsWith("/api/claims") && init?.method === "POST") {
      submittedMake = JSON.parse(init.body as string).vehicle.make;
      return new Response(JSON.stringify(createdClaim), { status: 201 });
    }
    return new Response(JSON.stringify(createdClaim));
  });
  sessionStorage.setItem(
    "claim-assistant-session",
    JSON.stringify(adjusterSession),
  );
  const user = userEvent.setup();
  renderRoute("/claims/new");

  expect(await screen.findByText("Claim information")).toBeVisible();
  expect(screen.getByText("Current")).toBeVisible();
  await user.click(screen.getByLabelText("Vehicle make"));
  await user.click(await screen.findByRole("option", { name: "Toyota" }));
  await user.click(screen.getByRole("button", { name: "Tiếng Việt" }));

  expect(await screen.findByText("Thông tin hồ sơ")).toBeVisible();
  expect(localStorage.getItem("app.language")).toBe("vi");
  await user.type(
    document.querySelector('input[name="incident_at"]')!,
    "2026-09-09T08:30",
  );
  await user.type(
    document.querySelector('input[name="incident_location"]')!,
    "District 1",
  );
  await user.type(
    document.querySelector('input[name="incident_description"]')!,
    "Rear impact.",
  );

  await user.type(screen.getByLabelText("Tên người yêu cầu"), "Mai Nguyen");
  await user.type(screen.getByLabelText("Dòng xe"), "Camry");
  await user.type(screen.getByLabelText("Năm sản xuất"), "2022");
  await user.click(screen.getByRole("button", { name: "Tạo hồ sơ" }));

  expect(submittedMake).toBe("Toyota");
});

test("vehicle make autocomplete renders its empty state", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const path = input instanceof Request ? input.url : String(input);
    if (path.endsWith("/api/auth/me"))
      return new Response(JSON.stringify(adjusterSession.user));
    if (path.includes("/api/vehicle-makes"))
      return new Response(JSON.stringify([]));
    return new Response(JSON.stringify([]));
  });
  sessionStorage.setItem(
    "claim-assistant-session",
    JSON.stringify(adjusterSession),
  );
  const user = userEvent.setup();
  renderRoute("/claims/new");

  await user.click(await screen.findByLabelText(/vehicle make/i));
  expect(
    await screen.findByText("No vehicle manufacturers are available."),
  ).toBeVisible();
});

test("vehicle make autocomplete renders its loading state", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const path = input instanceof Request ? input.url : String(input);
    if (path.endsWith("/api/auth/me"))
      return new Response(JSON.stringify(adjusterSession.user));
    if (path.includes("/api/vehicle-makes"))
      return new Promise<Response>(() => {});
    return new Response(JSON.stringify([]));
  });
  sessionStorage.setItem(
    "claim-assistant-session",
    JSON.stringify(adjusterSession),
  );
  renderRoute("/claims/new");

  expect(await screen.findByRole("status")).toHaveTextContent(
    "Loading vehicle manufacturers...",
  );
});

test("claim detail blocks analysis until all required evidence is present", async () => {
  const draftClaim = {
    id: "CLM-000051",
    claimant_name: "Mai Nguyen",
    vehicle: {
      make: "Toyota",
      model: "Camry",
      year: 2022,
      license_plate: null,
      vin: null,
    },
    incident: {
      occurred_at: "2026-09-09T01:30:00Z",
      location: "District 1",
      description: "Rear impact.",
    },
    status: "DRAFT",
    created_at: "2026-09-08T00:00:00Z",
    updated_at: "2026-09-08T00:00:00Z",
    evidence: [],
    latest_damage_analysis: null,
    latest_analysis_run: null,
  };
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    if (String(input).endsWith("/api/auth/me"))
      return new Response(JSON.stringify(adjusterSession.user));
    return new Response(JSON.stringify(draftClaim));
  });
  sessionStorage.setItem(
    "claim-assistant-session",
    JSON.stringify(adjusterSession),
  );
  renderRoute("/claims/CLM-000051");

  expect(await screen.findByText("Vehicle damage images")).toBeVisible();
  expect(screen.getByText("ID cards")).toBeVisible();
  expect(screen.getByRole("button", { name: /^analyze$/i })).toBeDisabled();
  expect(screen.getByText(/5 required evidence section/i)).toBeVisible();
});

test("adjuster uploads evidence through its dedicated category section", async () => {
  let currentClaim = {
    id: "CLM-000061",
    claimant_name: "Mai Nguyen",
    vehicle: {
      make: "Toyota",
      model: "Camry",
      year: 2022,
      license_plate: null,
      vin: null,
    },
    status: "DRAFT",
    created_at: "2026-09-08T00:00:00Z",
    updated_at: "2026-09-08T00:00:00Z",
    evidence: [] as EvidenceItem[],
  };
  let uploadedCategory = "";
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    if (String(input).endsWith("/api/auth/me"))
      return new Response(JSON.stringify(adjusterSession.user));
    if (String(input).endsWith("/evidence") && init?.method === "POST") {
      uploadedCategory = (init.body as FormData).get("categories") as string;
      currentClaim = {
        ...currentClaim,
        evidence: [
          {
            id: 1,
            category: uploadedCategory as EvidenceCategory,
            original_filename: "policy.pdf",
            content_type: "application/pdf",
            file_size: 12,
            uploaded_at: "2026-09-08T00:00:00Z",
            content_url: "/api/claims/CLM-000061/evidence/1/content",
          },
        ],
      };
    }
    return new Response(JSON.stringify(currentClaim));
  });
  sessionStorage.setItem(
    "claim-assistant-session",
    JSON.stringify(adjusterSession),
  );
  const user = userEvent.setup();
  renderRoute("/claims/CLM-000061");

  await user.upload(
    await screen.findByLabelText(/select files for insurance policies/i),
    new File(["document"], "policy.pdf", { type: "application/pdf" }),
  );

  expect(await screen.findByText("Insurance policies")).toBeVisible();
  expect(uploadedCategory).toBe("INSURANCE_POLICY");
});

test("evidence cards render a constrained thumbnail for uploaded images", async () => {
  const imageEvidence: EvidenceItem = {
    id: 1,
    category: "VEHICLE_DAMAGE_IMAGE",
    original_filename: "repair.jpg",
    content_type: "image/jpeg",
    file_size: 20,
    uploaded_at: "2026-09-08T00:00:00Z",
    content_url: "/api/claims/CLM-000062/evidence/1/content",
  };
  const claim: ClaimDetail = {
    id: "CLM-000062",
    claimant_name: "Mai Nguyen",
    vehicle: {
      make: "Toyota",
      model: "Camry",
      year: 2022,
      license_plate: null,
      vin: null,
    },
    incident: null,
    status: "DRAFT",
    created_at: "2026-09-08T00:00:00Z",
    updated_at: "2026-09-08T00:00:00Z",
    evidence: [imageEvidence],
    latest_damage_analysis: null,
    latest_analysis_run: null,
    copilot_review_history: [],
  };
  vi.stubGlobal("URL", {
    createObjectURL: () => "blob:evidence-preview",
    revokeObjectURL: () => undefined,
  });
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const path = String(input);
    if (path.endsWith("/api/auth/me"))
      return new Response(JSON.stringify(adjusterSession.user));
    if (path.endsWith("/content"))
      return new Response(new Blob(["image"], { type: "image/jpeg" }));
    return new Response(JSON.stringify(claim));
  });
  sessionStorage.setItem(
    "claim-assistant-session",
    JSON.stringify(adjusterSession),
  );
  renderRoute("/claims/CLM-000062");

  const preview = await screen.findByRole("img", { name: "repair.jpg" });
  expect(preview).toHaveClass("size-20");
  expect(preview.closest("a")).toHaveAttribute("href", "blob:evidence-preview");
  expect(preview.closest("a")).toHaveAttribute("target", "_blank");
  expect(preview.closest("a")).toHaveAttribute("rel", "noopener noreferrer");
});

test("deleting evidence requires confirmation", async () => {
  const evidence: EvidenceItem = {
    id: 1,
    category: "ID_CARD",
    original_filename: "claimant-id.jpg",
    content_type: "image/jpeg",
    file_size: 20,
    uploaded_at: "2026-09-08T00:00:00Z",
    content_url: "/api/claims/CLM-000063/evidence/1/content",
  };
  let deleted = false;
  let claim = {
    id: "CLM-000063",
    claimant_name: "Mai Nguyen",
    vehicle: { make: "Toyota", model: "Camry", year: 2022 },
    incident: null,
    status: "DRAFT",
    created_at: "2026-09-08T00:00:00Z",
    updated_at: "2026-09-08T00:00:00Z",
    evidence: [evidence],
    latest_damage_analysis: null,
    latest_analysis_run: null,
    copilot_review_history: [],
  } as unknown as ClaimDetail;
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const path = String(input);
    if (path.endsWith("/api/auth/me"))
      return new Response(JSON.stringify(adjusterSession.user));
    if (path.endsWith("/content"))
      return new Response(new Blob(["image"], { type: "image/jpeg" }));
    if (path.endsWith("/evidence/1") && init?.method === "DELETE") {
      deleted = true;
      claim = { ...claim, evidence: [] };
    }
    return new Response(JSON.stringify(claim));
  });
  sessionStorage.setItem(
    "claim-assistant-session",
    JSON.stringify(adjusterSession),
  );
  const user = userEvent.setup();
  renderRoute("/claims/CLM-000063");

  await user.click(
    await screen.findByRole("button", { name: "Remove claimant-id.jpg" }),
  );
  const dialog = await screen.findByRole("dialog");
  expect(within(dialog).getByText("Delete evidence?")).toBeVisible();
  expect(within(dialog).getByText(/claimant-id\.jpg/)).toBeVisible();
  expect(deleted).toBe(false);

  await user.click(within(dialog).getByRole("button", { name: "Delete" }));
  expect(deleted).toBe(true);
  expect(screen.queryByText("claimant-id.jpg")).not.toBeInTheDocument();
});

test("legacy claim data remains readable and requests the missing workflow information", async () => {
  const damageImage: EvidenceItem = {
    id: 1,
    category: "VEHICLE_DAMAGE_IMAGE",
    original_filename: "no-damage.jpg",
    content_type: "image/jpeg",
    file_size: 20,
    uploaded_at: "2026-09-08T00:00:00Z",
    content_url: "/api/claims/CLM-000071/evidence/1/content",
  };
  let currentClaim: ClaimDetail = {
    id: "CLM-000071",
    claimant_name: "Mai Nguyen",
    vehicle: {
      make: "Toyota",
      model: "Camry",
      year: 2022,
      license_plate: null,
      vin: null,
    },
    status: "ANALYZING",
    created_at: "2026-09-08T00:00:00Z",
    updated_at: "2026-09-08T00:00:00Z",
    evidence: [damageImage],
    latest_damage_analysis: null,
  };
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    if (String(input).endsWith("/api/auth/me"))
      return new Response(JSON.stringify(adjusterSession.user));
    if (String(input).endsWith("/damage-analysis") && init?.method === "POST") {
      currentClaim = {
        ...currentClaim,
        status: "REVIEW_REQUIRED",
        latest_damage_analysis: {
          id: "DA-000001",
          assessment: "NO_DAMAGE",
          detections: [],
          warning:
            "No significant vehicle damage was detected. This does not guarantee the vehicle is undamaged.",
          rules: {
            confidence_threshold: 0.7,
            repair_max_percentage: 40,
            replacement_min_percentage: 60,
          },
          reference_price_status: "NOT_REQUESTED",
          reference_prices: [],
          copilot_conclusion: {
            id: 1,
            status: "FALLBACK",
            recommendation: "MANUAL_ADJUSTER_REVIEW",
            summary:
              "No normalized damage finding supports a no-damage assessment. An adjuster must review this case before any final decision.",
            fallback_summary:
              "No normalized damage finding supports a no-damage assessment. An adjuster must review this case before any final decision.",
            failure_reason: null,
            provider_model: null,
            findings: [],
            warnings: [
              "No significant vehicle damage was detected. This does not guarantee the vehicle is undamaged.",
            ],
            reference_prices: [],
            review_history: [],
          },
          created_at: "2026-09-08T00:01:00Z",
        },
      };
      return new Response(JSON.stringify(currentClaim.latest_damage_analysis));
    }
    if (
      String(input).includes("/copilot-conclusions/1/review") &&
      init?.method === "POST"
    ) {
      currentClaim = {
        ...currentClaim,
        status: "AI_APPROVED",
        copilot_review_history: [
          {
            claim_id: "CLM-000071",
            conclusion_id: 1,
            status: "APPROVED",
            reason_category: null,
            comment: null,
            reviewer: "adjuster@example.com",
            reviewed_at: "2026-09-08T00:02:00Z",
          },
        ],
        latest_damage_analysis: {
          ...currentClaim.latest_damage_analysis!,
          copilot_conclusion: {
            ...currentClaim.latest_damage_analysis!.copilot_conclusion!,
            review_history: [
              {
                claim_id: "CLM-000071",
                conclusion_id: 1,
                status: "APPROVED",
                reason_category: null,
                comment: null,
                reviewer: "adjuster@example.com",
                reviewed_at: "2026-09-08T00:02:00Z",
              },
            ],
          },
        },
      };
    }
    return new Response(JSON.stringify(currentClaim));
  });
  sessionStorage.setItem(
    "claim-assistant-session",
    JSON.stringify(adjusterSession),
  );
  renderRoute("/claims/CLM-000071");

  expect(
    await screen.findByText(/complete incident information first/i),
  ).toBeVisible();
  expect(screen.getByRole("button", { name: /^analyze$/i })).toBeDisabled();
  expect(screen.getByText("no-damage.jpg")).toBeVisible();
});

test("adjuster reviews grouped workflow results and submits a noted human decision", async () => {
  const evidence: EvidenceItem[] = [
    "VEHICLE_DAMAGE_IMAGE",
    "ID_CARD",
    "INSURANCE_POLICY",
    "VEHICLE_REGISTRATION",
    "DRIVER_LICENSE",
  ].map((category, index) => ({
    id: index + 1,
    category: category as EvidenceCategory,
    original_filename: `${category.toLowerCase()}.jpg`,
    content_type: "image/jpeg",
    file_size: 20,
    uploaded_at: "2026-09-08T00:00:00Z",
    content_url: `/api/claims/CLM-000081/evidence/${index + 1}/content`,
  }));
  evidence.push({
    id: 6,
    category: "ID_CARD",
    original_filename: "id_card_back.jpg",
    content_type: "image/jpeg",
    file_size: 18,
    uploaded_at: "2026-09-08T00:00:00Z",
    content_url: "/api/claims/CLM-000081/evidence/6/content",
  });
  const damageAnalysis = {
    id: "DA-000008",
    assessment: "NO_DAMAGE" as const,
    detections: [],
    warning: null,
    rules: {
      confidence_threshold: 0.7,
      repair_max_percentage: 40,
      replacement_min_percentage: 60,
    },
    reference_price_status: "NOT_REQUESTED" as const,
    reference_prices: [],
    copilot_conclusion: {
      id: 8,
      status: "FALLBACK" as const,
      recommendation: "MANUAL_ADJUSTER_REVIEW" as const,
      summary:
        "Submitted evidence is consistent and still requires adjuster review.",
      fallback_summary: null,
      failure_reason: null,
      provider_model: null,
      findings: [],
      warnings: [],
      reference_prices: [],
      review_history: [],
      validity_percentage: 85,
      review_status: "REVIEW_REQUIRED",
      evidence_references: evidence.map((item) => ({
        id: item.id,
        category: item.category,
        original_filename: item.original_filename,
      })),
    },
    created_at: "2026-09-08T00:01:00Z",
  };
  let submittedReview: unknown = null;
  const currentClaim = {
    id: "CLM-000081",
    claimant_name: "Mai Nguyen",
    vehicle: {
      make: "Toyota",
      model: "Camry",
      year: 2022,
      license_plate: "51H-123.45",
      vin: null,
    },
    incident: {
      occurred_at: "2026-09-08T00:00:00Z",
      location: "District 1",
      description: "Rear impact.",
    },
    status: "REVIEW_REQUIRED",
    created_at: "2026-09-08T00:00:00Z",
    updated_at: "2026-09-08T00:01:00Z",
    evidence,
    latest_damage_analysis: damageAnalysis,
    latest_analysis_run: {
      id: 8,
      status: "PARTIAL",
      damage_status: "COMPLETED",
      damage_analysis: damageAnalysis,
      document_analyses: [
        {
          id: 10,
          document_type: "ID_CARD",
          status: "COMPLETED",
          warnings: [],
          fields: [
            {
              id: 11,
              key: "full_name",
              label: "Full name",
              original_ai_value: "Nguyen Van A",
              reviewed_value: "Nguyen Van A",
              confidence: 0.97,
              status: "VALID",
            },
          ],
        },
      ],
      document_ocr_results: [
        {
          id: 101,
          source_evidence_id: 2,
          document_type: "ID_CARD",
          original_filename: "id_card.jpg",
          content_type: "image/jpeg",
          status: "COMPLETED",
          raw_text: "Full name: Nguyen Van A\nIdentity number: 079203001234",
          adapter_name: "deepdoc-vietocr",
          adapter_metadata: {},
          warning: null,
          created_at: "2026-09-08T00:00:01Z",
          processed_at: "2026-09-08T00:00:02Z",
          field_validations: [
            {
              id: 201,
              analysis_run_id: 8,
              document_ocr_result_id: 101,
              source_evidence_id: 2,
              field_key: "full_name",
              prompt_version: "document-fields-v1",
              ocr_value: "Nguyen Van A",
              normalized_value: "Nguyen Van A",
              status: "VALID",
              confidence: 0.97,
              summary: "The holder name is readable.",
              warnings: [],
            },
          ],
        },
        {
          id: 102,
          source_evidence_id: 6,
          document_type: "ID_CARD",
          original_filename: "id_card_back.jpg",
          content_type: "image/jpeg",
          status: "COMPLETED",
          raw_text: "Full name: Nguyen Van A",
          adapter_name: "deepdoc-vietocr",
          adapter_metadata: {},
          warning: null,
          created_at: "2026-09-08T00:00:01Z",
          processed_at: "2026-09-08T00:00:02Z",
          field_validations: [
            {
              id: 202,
              analysis_run_id: 8,
              document_ocr_result_id: 102,
              source_evidence_id: 6,
              field_key: "full_name",
              prompt_version: "document-fields-v1",
              ocr_value: "Nguyen Van A",
              normalized_value: "Nguyen Van A",
              status: "LLM_UNAVAILABLE",
              confidence: 0,
              summary: "Full name requires manual review.",
              warnings: ["Field validation unavailable (RateLimitError)."],
            },
          ],
        },
        {
          id: 103,
          source_evidence_id: 3,
          document_type: "INSURANCE_POLICY",
          original_filename: "insurance_policy.jpg",
          content_type: "image/jpeg",
          status: "FAILED",
          raw_text: null,
          adapter_name: null,
          adapter_metadata: {},
          warning: "OCR processing failed for this image.",
          created_at: "2026-09-08T00:00:01Z",
          processed_at: "2026-09-08T00:00:02Z",
          field_validations: [],
        },
      ],
      consistency_checks: [
        {
          id: 301,
          field_validation_id: 201,
          source_evidence_id: 2,
          field_key: "full_name",
          claim_value: "Mai Nguyen",
          document_value: "Nguyen Van A",
          status: "MISMATCH",
          explanation:
            "Document value differs from Claim Information and requires manual review.",
        },
      ],
      failure_reason: null,
      created_at: "2026-09-08T00:00:00Z",
      started_at: "2026-09-08T00:00:01Z",
      completed_at: "2026-09-08T00:00:02Z",
    },
    copilot_review_history: [],
  } as unknown as ClaimDetail;
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    if (String(input).endsWith("/api/auth/me"))
      return new Response(JSON.stringify(adjusterSession.user));
    if (
      String(input).includes("/copilot-conclusions/8/review") &&
      init?.method === "POST"
    )
      submittedReview = JSON.parse(init.body as string);
    return new Response(JSON.stringify(currentClaim));
  });
  sessionStorage.setItem(
    "claim-assistant-session",
    JSON.stringify(adjusterSession),
  );
  const user = userEvent.setup();
  renderRoute("/claims/CLM-000081");

  expect(await screen.findByText("Document analysis")).toBeVisible();
  expect(screen.getByText("Partial results available")).toBeVisible();
  const front = screen.getByRole("article", { name: "id_card.jpg" });
  const back = screen.getByRole("article", { name: "id_card_back.jpg" });
  const failedPolicy = screen.getByRole("article", {
    name: "insurance_policy.jpg",
  });
  expect(within(front).getByText("The holder name is readable.")).toBeVisible();
  expect(
    within(front).getByLabelText("Full name normalized value"),
  ).toBeDisabled();
  expect(within(front).getByText("Mismatch")).toBeVisible();
  expect(within(front).getByText(/requires manual review/i)).toBeVisible();
  expect(within(back).getByText("AI unavailable")).toBeVisible();
  expect(within(back).getByText("Comparison unavailable")).toBeVisible();
  expect(within(back).getByText(/field validation unavailable/i)).toBeVisible();
  expect(within(failedPolicy).getByText("Failed")).toBeVisible();
  expect(
    within(failedPolicy).getByText(/ocr processing failed/i),
  ).toBeVisible();
  expect(screen.getAllByText("ID cards")).toHaveLength(2);
  expect(screen.getByText("No significant damage detections")).toBeVisible();
  expect(screen.getByText("85%")).toBeVisible();
  expect(
    screen.getByText(/not an automatic approval probability/i),
  ).toBeVisible();
  await user.type(
    screen.getByLabelText("Review note"),
    "Evidence checked against the submitted documents.",
  );
  await user.click(
    screen.getByRole("button", { name: /submit human review/i }),
  );
  expect(submittedReview).toEqual({
    status: "APPROVED",
    comment: "Evidence checked against the submitted documents.",
  });
});

test("adjuster reviews persisted identity extraction without a confidence score", async () => {
  const evidence: EvidenceItem = {
    id: 2,
    category: "ID_CARD",
    original_filename: "claimant-id.jpg",
    content_type: "image/jpeg",
    file_size: 20,
    uploaded_at: "2026-09-08T00:00:00Z",
    content_url: "/api/claims/CLM-000082/evidence/2/content",
  };
  const field = {
    id: 202,
    analysis_run_id: 9,
    extraction_result_id: 302,
    source_evidence_id: 2,
    field_key: "full_name",
    ai_extracted_value: "Nguyen Van A",
    confirmed_value: "Nguyen Van A",
    prompt_version: "document-extraction-v1",
    schema_version: "document-extraction-schema-v1",
    created_at: "2026-09-08T00:00:02Z",
    updated_at: "2026-09-08T00:00:02Z",
  };
  const claim = {
    id: "CLM-000082",
    claimant_name: "Mai Nguyen",
    vehicle: {
      make: "Toyota",
      model: "Camry",
      year: 2022,
      license_plate: "51H-123.45",
      vin: null,
    },
    incident: {
      occurred_at: "2026-09-08T00:00:00Z",
      location: "District 1",
      description: "Rear impact.",
    },
    status: "REVIEW_REQUIRED",
    created_at: "2026-09-08T00:00:00Z",
    updated_at: "2026-09-08T00:01:00Z",
    evidence: [evidence],
    latest_damage_analysis: null,
    latest_analysis_run: {
      id: 9,
      status: "COMPLETED",
      damage_status: "FAILED",
      damage_analysis: null,
      document_analyses: [],
      document_ocr_results: [
        {
          id: 102,
          source_evidence_id: 2,
          document_type: "ID_CARD",
          original_filename: "claimant-id.jpg",
          content_type: "image/jpeg",
          status: "COMPLETED",
          raw_text: "Full name: Nguyen Van A",
          adapter_name: "deepdoc-vietocr",
          adapter_metadata: {},
          warning: null,
          created_at: "2026-09-08T00:00:01Z",
          processed_at: "2026-09-08T00:00:02Z",
          extraction: {
            id: 302,
            analysis_run_id: 9,
            document_ocr_result_id: 102,
            source_evidence_id: 2,
            document_type: "ID_CARD",
            status: "COMPLETED",
            prompt_version: "document-extraction-v1",
            schema_version: "document-extraction-schema-v1",
            warning: null,
            created_at: "2026-09-08T00:00:02Z",
            processed_at: "2026-09-08T00:00:02Z",
            fields: [field],
          },
          field_validations: [],
        },
      ],
      consistency_checks: [],
      failure_reason: null,
      created_at: "2026-09-08T00:00:00Z",
      started_at: "2026-09-08T00:00:01Z",
      completed_at: "2026-09-08T00:00:02Z",
    },
    copilot_review_history: [],
  } as unknown as ClaimDetail;
  let submittedField: unknown = null;
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const path = String(input);
    if (path.endsWith("/api/auth/me"))
      return new Response(JSON.stringify(adjusterSession.user));
    if (path.endsWith("/content"))
      return new Response(new Blob(["image"], { type: "image/jpeg" }));
    if (path.endsWith("/extraction-fields") && init?.method === "PUT") {
      submittedField = JSON.parse(init.body as string);
      field.confirmed_value = (
        submittedField as {
          fields: Array<{ id: number; confirmed_value: string }>;
        }
      ).fields.find((item) => item.id === field.id)!.confirmed_value;
    }
    return new Response(JSON.stringify(claim));
  });
  sessionStorage.setItem(
    "claim-assistant-session",
    JSON.stringify(adjusterSession),
  );
  const user = userEvent.setup();
  renderRoute("/claims/CLM-000082");

  await screen.findByRole("article", { name: "claimant-id.jpg" });
  const identitySection = screen.getByRole("region", { name: "ID cards" });
  const input = within(identitySection).getByLabelText(
    "Full name confirmed value",
  );
  expect(within(identitySection).getByText("Nguyen Van A")).toBeVisible();
  expect(within(identitySection).queryByText("97%")).not.toBeInTheDocument();
  await user.clear(input);
  await user.type(input, "Mai Nguyen");
  await user.click(screen.getByRole("button", { name: "Save all fields" }));

  expect(submittedField).toEqual({
    fields: [{ id: 202, confirmed_value: "Mai Nguyen" }],
  });
  expect(input).toHaveValue("Mai Nguyen");
});

test("adjuster reviews registration and driver license extraction fields", async () => {
  const registrationEvidence: EvidenceItem = {
    id: 3,
    category: "VEHICLE_REGISTRATION",
    original_filename: "registration.jpg",
    content_type: "image/jpeg",
    file_size: 20,
    uploaded_at: "2026-09-08T00:00:00Z",
    content_url: "/api/claims/CLM-000083/evidence/3/content",
  };
  const driverEvidence: EvidenceItem = {
    ...registrationEvidence,
    id: 4,
    category: "DRIVER_LICENSE",
    original_filename: "driver-license.jpg",
    content_url: "/api/claims/CLM-000083/evidence/4/content",
  };
  const extractedField = (
    id: number,
    sourceEvidenceId: number,
    fieldKey: string,
    value: string | null,
  ) => ({
    id,
    analysis_run_id: 10,
    extraction_result_id: sourceEvidenceId + 300,
    source_evidence_id: sourceEvidenceId,
    field_key: fieldKey,
    ai_extracted_value: value,
    confirmed_value: value,
    prompt_version: "document-extraction-v1",
    schema_version: "document-extraction-schema-v1",
    created_at: "2026-09-08T00:00:02Z",
    updated_at: "2026-09-08T00:00:02Z",
  });
  const registrationFields = [
    extractedField(301, 3, "vehicle_owner", "Nguyen Van A"),
    extractedField(302, 3, "vehicle_brand", "Toyota"),
    extractedField(303, 3, "vehicle_type", "Ô tô con"),
    extractedField(304, 3, "license_plate", "51H-123.45"),
  ];
  const driverFields = [
    extractedField(401, 4, "license_number", "079012345678"),
    extractedField(402, 4, "full_name", null),
    extractedField(403, 4, "expiry_date", null),
  ];
  const ocrResult = (
    id: number,
    evidence: EvidenceItem,
    fields: ReturnType<typeof extractedField>[],
  ) => ({
    id,
    source_evidence_id: evidence.id,
    document_type: evidence.category,
    original_filename: evidence.original_filename,
    content_type: evidence.content_type,
    status: "COMPLETED" as const,
    raw_text: `OCR for ${evidence.original_filename}`,
    adapter_name: "deepdoc-vietocr",
    adapter_metadata: {},
    warning: null,
    created_at: "2026-09-08T00:00:01Z",
    processed_at: "2026-09-08T00:00:02Z",
    extraction: {
      id: evidence.id + 300,
      analysis_run_id: 10,
      document_ocr_result_id: id,
      source_evidence_id: evidence.id,
      document_type: evidence.category,
      status: "COMPLETED" as const,
      prompt_version: "document-extraction-v1",
      schema_version: "document-extraction-schema-v1",
      warning: null,
      created_at: "2026-09-08T00:00:02Z",
      processed_at: "2026-09-08T00:00:02Z",
      fields,
    },
    field_validations: [],
  });
  const claim = {
    id: "CLM-000083",
    claimant_name: "Mai Nguyen",
    vehicle: {
      make: "Toyota",
      model: "Camry",
      year: 2022,
      license_plate: "51H-123.45",
      vin: null,
    },
    incident: {
      occurred_at: "2026-09-08T00:00:00Z",
      location: "District 1",
      description: "Rear impact.",
    },
    status: "REVIEW_REQUIRED",
    created_at: "2026-09-08T00:00:00Z",
    updated_at: "2026-09-08T00:01:00Z",
    evidence: [registrationEvidence, driverEvidence],
    latest_damage_analysis: null,
    latest_analysis_run: {
      id: 10,
      status: "COMPLETED",
      damage_status: "FAILED",
      damage_analysis: null,
      document_analyses: [],
      document_ocr_results: [
        ocrResult(103, registrationEvidence, registrationFields),
        ocrResult(104, driverEvidence, driverFields),
      ],
      consistency_checks: [],
      failure_reason: null,
      created_at: "2026-09-08T00:00:00Z",
      started_at: "2026-09-08T00:00:01Z",
      completed_at: "2026-09-08T00:00:02Z",
    },
    copilot_review_history: [],
  } as unknown as ClaimDetail;
  let submittedField: unknown = null;
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const path = String(input);
    if (path.endsWith("/api/auth/me"))
      return new Response(JSON.stringify(adjusterSession.user));
    if (path.endsWith("/content"))
      return new Response(new Blob(["image"], { type: "image/jpeg" }));
    if (path.endsWith("/extraction-fields") && init?.method === "PUT") {
      submittedField = JSON.parse(init.body as string);
      registrationFields[3].confirmed_value = (
        submittedField as {
          fields: Array<{ id: number; confirmed_value: string }>;
        }
      ).fields.find((item) => item.id === 304)!.confirmed_value;
    }
    return new Response(JSON.stringify(claim));
  });
  sessionStorage.setItem(
    "claim-assistant-session",
    JSON.stringify(adjusterSession),
  );
  const user = userEvent.setup();
  renderRoute("/claims/CLM-000083");

  await screen.findByRole("article", { name: "registration.jpg" });
  const registration = screen.getByRole("region", {
    name: "Vehicle registrations",
  });
  const driver = screen.getByRole("region", { name: "Driver licenses" });
  expect(
    within(registration).getByLabelText("Vehicle type confirmed value"),
  ).toHaveValue("Ô tô con");
  const plate = within(registration).getByLabelText(
    "License plate confirmed value",
  );
  expect(
    within(driver).getByLabelText("License number confirmed value"),
  ).toHaveValue("079012345678");
  expect(within(driver).getAllByText("Not provided")).toHaveLength(2);
  expect(within(registration).queryByText(/%/)).not.toBeInTheDocument();

  await user.clear(plate);
  await user.type(plate, "51H-999.99");
  await user.click(screen.getByRole("button", { name: "Save all fields" }));
  expect(
    (
      submittedField as {
        fields: Array<{ id: number; confirmed_value: string | null }>;
      }
    ).fields.find((item) => item.id === 304),
  ).toEqual({ id: 304, confirmed_value: "51H-999.99" });
  expect(
    (
      submittedField as {
        fields: Array<{ id: number; confirmed_value: string | null }>;
      }
    ).fields,
  ).toHaveLength(7);
});

test("admin can update global assessment rules from the configuration page", async () => {
  let configuration: AssessmentRuleConfiguration = {
    values: {
      confidence_threshold: 0.7,
      repair_max_percentage: 40,
      replacement_min_percentage: 60,
    },
    updated_by: null,
    updated_at: "2026-09-08T00:00:00Z",
  };
  let savedValues: unknown = null;
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    if (String(input).endsWith("/api/auth/me"))
      return new Response(JSON.stringify(adminSession.user));
    if (String(input).endsWith("/vehicle-makes"))
      return new Response(
        JSON.stringify([{ id: 1, name: "Toyota", is_active: true }]),
      );
    if (String(input).endsWith("/assessment-rules/history"))
      return new Response(JSON.stringify([]));
    if (String(input).endsWith("/assessment-rules") && init?.method === "PUT") {
      savedValues = JSON.parse(init.body as string);
      configuration = {
        ...configuration,
        values: savedValues as typeof configuration.values,
        updated_by: "admin@example.com",
      };
      return new Response(JSON.stringify(configuration));
    }
    return new Response(JSON.stringify(configuration));
  });
  sessionStorage.setItem(
    "claim-assistant-session",
    JSON.stringify(adminSession),
  );
  const user = userEvent.setup();
  renderRoute("/admin");

  await user.clear(await screen.findByLabelText(/confidence threshold/i));
  await user.type(screen.getByLabelText(/confidence threshold/i), "0.8");
  await user.click(screen.getByRole("button", { name: /save rules/i }));

  expect(savedValues).toEqual({
    confidence_threshold: 0.8,
    repair_max_percentage: 40,
    replacement_min_percentage: 60,
  });
  expect(
    await screen.findByText(/last changed by admin@example.com/i),
  ).toBeVisible();
});

test("admin can create, disable, and re-enable a vehicle manufacturer", async () => {
  const configuration: AssessmentRuleConfiguration = {
    values: {
      confidence_threshold: 0.7,
      repair_max_percentage: 40,
      replacement_min_percentage: 60,
    },
    updated_by: null,
    updated_at: "2026-09-08T00:00:00Z",
  };
  let manufacturers = [{ id: 1, name: "Toyota", is_active: true }];
  const updates: Array<{ id: number; name: string; is_active: boolean }> = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const path = input instanceof Request ? input.url : String(input);
    if (path.endsWith("/api/auth/me"))
      return new Response(JSON.stringify(adminSession.user));
    if (path.endsWith("/assessment-rules/history"))
      return new Response(JSON.stringify([]));
    if (path.endsWith("/assessment-rules"))
      return new Response(JSON.stringify(configuration));
    if (path.endsWith("/api/admin/vehicle-makes") && init?.method === "POST") {
      const created = {
        id: 2,
        name: JSON.parse(init.body as string).name,
        is_active: true,
      };
      manufacturers = [...manufacturers, created];
      return new Response(JSON.stringify(created), { status: 201 });
    }
    const manufacturerMatch = path.match(/\/api\/admin\/vehicle-makes\/(\d+)$/);
    if (manufacturerMatch && init?.method === "PUT") {
      const values = JSON.parse(init.body as string) as {
        name: string;
        is_active: boolean;
      };
      const id = Number(manufacturerMatch[1]);
      updates.push({ id, ...values });
      manufacturers = manufacturers.map((manufacturer) =>
        manufacturer.id === id ? { id, ...values } : manufacturer,
      );
      return new Response(
        JSON.stringify(
          manufacturers.find((manufacturer) => manufacturer.id === id),
        ),
      );
    }
    if (path.endsWith("/api/admin/vehicle-makes"))
      return new Response(JSON.stringify(manufacturers));
    return new Response(JSON.stringify([]));
  });
  sessionStorage.setItem(
    "claim-assistant-session",
    JSON.stringify(adminSession),
  );
  const user = userEvent.setup();
  renderRoute("/admin");

  expect(await screen.findByRole("table")).toBeVisible();
  expect(
    screen.getByRole("columnheader", { name: "Manufacturer name" }),
  ).toBeVisible();
  expect(screen.getByRole("columnheader", { name: "Status" })).toBeVisible();
  expect(screen.getByRole("columnheader", { name: "Actions" })).toBeVisible();

  await user.type(
    (await screen.findAllByLabelText("Manufacturer name"))[0],
    "BYD",
  );
  await user.click(screen.getByRole("button", { name: "Add manufacturer" }));
  expect(await screen.findByDisplayValue("BYD")).toBeVisible();

  await user.click(screen.getAllByRole("button", { name: "Disable" })[0]);
  expect(await screen.findByRole("button", { name: "Enable" })).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Enable" }));

  expect(updates).toEqual([
    { id: 1, name: "Toyota", is_active: false },
    { id: 1, name: "Toyota", is_active: true },
  ]);
});
