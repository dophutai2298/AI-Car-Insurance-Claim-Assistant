import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import i18n from "../../i18n";
import { PriceRecommendationPanel } from "./PriceRecommendationPanel";
import type { PriceRecommendation } from "./types";

describe("Price recommendation", () => {
  it("marks advice as stale after its confirmed inputs change", () => {
    render(
      <PriceRecommendationPanel
        isStale
        value={{
          recommendation: "SUPPORTS_REPAIR",
          rationale: "The earlier estimates supported repair.",
        }}
      />,
    );
    expect(screen.getByText("Earlier snapshot")).toBeVisible();
    expect(screen.getByText(/no longer current/)).toBeVisible();
    expect(screen.queryByText("Supports repair")).not.toBeInTheDocument();
  });
  it.each([
    ["SUPPORTS_REPAIR", "Supports repair"],
    ["SUPPORTS_REPLACEMENT", "Supports replacement"],
    ["MANUAL_REVIEW", "Manual pricing review required"],
  ] as const)("shows %s as informational advice", (recommendation, label) => {
    render(
      <PriceRecommendationPanel
        value={{
          recommendation,
          rationale: "Verified pricing requires adjuster inspection.",
        }}
      />,
    );
    expect(screen.getByText(label)).toBeVisible();
    expect(
      screen.getByText("Verified pricing requires adjuster inspection."),
    ).toBeVisible();
    expect(screen.getByText(/adjuster makes the final decision/)).toBeVisible();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("displays a Vietnamese rationale with the translated recommendation label", async () => {
    await i18n.changeLanguage("vi");
    const value: PriceRecommendation = {
      recommendation: "MANUAL_REVIEW",
      rationale: "Chưa có giá thay thế phù hợp cho nắp capo.",
    };
    render(<PriceRecommendationPanel value={value} />);
    expect(screen.getByText("Cần thẩm định giá thủ công")).toBeVisible();
    expect(screen.getByText(value.rationale)).toBeVisible();
    expect(
      screen.getByText(/chuyên viên thẩm định quyết định cuối cùng/),
    ).toBeVisible();
  });
});
