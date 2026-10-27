import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PricingOverview } from "./PricingOverview";
import type { AnalysisPricing, ReferencePartPrice } from "./types";
import i18n from "../../i18n";

const price: ReferencePartPrice = {
  part_identity: "hood",
  amount: 1900000,
  currency: "VND",
  price_type: "REPAIR_ESTIMATE",
  source_name: "Demo Vietnam price catalog (mock)",
  source_url: null,
  retrieved_at: "2026-01-01T00:00:00Z",
  effective_at: "2026-01-01T00:00:00Z",
  status: "FOUND",
  failure_reason: null,
  vehicle_make: "Toyota",
  vehicle_model: "Camry",
  vehicle_year: 2022,
};
const pricing: AnalysisPricing = {
  currency: "VND",
  repair_estimate: {
    status: "COMPLETE",
    total_amount: 1900000,
    known_subtotal: 1900000,
    priced_parts: 1,
    total_parts: 1,
  },
  replacement_part_price: {
    status: "INCOMPLETE",
    total_amount: null,
    known_subtotal: 8400000,
    priced_parts: 1,
    total_parts: 2,
  },
  line_items: [
    {
      part_identity: "hood",
      repair_estimate: price,
      replacement_part_price: {
        ...price,
        amount: null,
        status: "UNAVAILABLE",
        price_type: "REPLACEMENT_PART_PRICE",
      },
    },
  ],
};

describe("Pricing overview", () => {
  it("distinguishes provider failures from missing catalog matches", () => {
    render(
      <PricingOverview
        pricing={{
          ...pricing,
          line_items: [
            {
              ...pricing.line_items[0],
              replacement_part_price: {
                ...pricing.line_items[0].replacement_part_price,
                unavailable_reason: "PROVIDER_UNAVAILABLE",
              },
            },
          ],
        }}
        assessment="REPAIR_LIKELY"
      />,
    );
    expect(
      screen.getByText("Price lookup unavailable. Try again later."),
    ).toBeVisible();
    expect(screen.queryByText("No exact price match")).not.toBeInTheDocument();
  });
  it("shows assessment before estimates and breakdown, with explicit incomplete-price wording", () => {
    render(<PricingOverview pricing={pricing} assessment="REPAIR_LIKELY" />);
    const assessment = screen.getByText(/Damage assessment:/);
    const repair = screen.getByRole("heading", { name: "Repair estimate" });
    const table = screen.getByRole("table", {
      name: "Per-part price comparison",
    });
    expect(
      assessment.compareDocumentPosition(repair) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      repair.compareDocumentPosition(table) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(screen.getByText(/Known subtotal only/)).toBeVisible();
    expect(screen.getByText("No exact price match")).toBeVisible();
    expect(screen.getByText("Demo Vietnam price catalog (mock)")).toBeVisible();
    expect(screen.getByText(/adjuster makes the final decision/)).toBeVisible();
  });

  it("shows unavailable pricing and Vietnamese labels", async () => {
    await i18n.changeLanguage("vi");
    render(
      <PricingOverview
        pricing={{
          ...pricing,
          replacement_part_price: {
            status: "UNAVAILABLE",
            total_amount: null,
            known_subtotal: 0,
            priced_parts: 0,
            total_parts: 1,
          },
        }}
        assessment="REPAIR_LIKELY"
      />,
    );
    expect(screen.getByText("Chưa có giá")).toBeVisible();
    expect(
      screen.getByRole("table", { name: "Bảng so sánh giá từng phụ tùng" }),
    ).toBeVisible();
    expect(screen.getByText(/Giá chỉ mang tính tham khảo/)).toBeVisible();
  });
});
