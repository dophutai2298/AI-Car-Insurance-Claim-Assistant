import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router";
import { expect, test } from "vitest";

import { ClaimQueueTable } from "./ClaimQueueTable";

const claims = [
  {
    id: "CLM-000101",
    claimant: "Mai Nguyen",
    vehicle: "2024 Toyota Camry",
    status: "REVIEW_REQUIRED" as const,
    updatedAt: "2026-09-24T08:00:00Z",
  },
  {
    id: "CLM-000102",
    claimant: "An Tran",
    vehicle: "2023 Ford Ranger",
    status: "AI_APPROVED" as const,
    updatedAt: "2026-09-23T08:00:00Z",
  },
];

test("filters claims by text and review status, then restores the queue", async () => {
  const user = userEvent.setup();
  render(
    <MemoryRouter>
      <ClaimQueueTable claims={claims} />
    </MemoryRouter>,
  );

  await user.type(screen.getByLabelText("Search claims"), "Ford");
  expect(screen.getByRole("link", { name: "CLM-000102" })).toBeVisible();
  expect(
    screen.queryByRole("link", { name: "CLM-000101" }),
  ).not.toBeInTheDocument();

  await user.selectOptions(screen.getByLabelText("Status"), "REVIEW_REQUIRED");
  expect(
    screen.getByText("No claims match the selected filters."),
  ).toBeVisible();

  await user.click(screen.getByRole("button", { name: "Clear filters" }));
  expect(screen.getByRole("link", { name: "CLM-000101" })).toBeVisible();
  expect(screen.getByRole("link", { name: "CLM-000102" })).toBeVisible();
});

test("paginates filtered claims and resets to the first page when page size changes", async () => {
  const user = userEvent.setup();
  const pagedClaims = Array.from({ length: 12 }, (_, index) => ({
    id: `CLM-${String(index + 201).padStart(6, "0")}`,
    claimant: `Claimant ${index + 1}`,
    vehicle: "2024 Toyota Camry",
    status: "DRAFT" as const,
    updatedAt: "2026-09-24T08:00:00Z",
  }));
  render(
    <MemoryRouter>
      <ClaimQueueTable claims={pagedClaims} />
    </MemoryRouter>,
  );

  expect(screen.getByText("Showing 1-10 of 12 claims")).toBeVisible();
  expect(
    screen.queryByRole("link", { name: "CLM-000211" }),
  ).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Next page" }));
  expect(screen.getByText(/^Page/)).toHaveTextContent("Page 2 of 2");
  expect(screen.getByRole("link", { name: "CLM-000211" })).toBeVisible();

  await user.selectOptions(screen.getByLabelText("Rows per page"), "20");
  expect(await screen.findByText("Page 1 of 1")).toBeVisible();
  expect(screen.getByRole("link", { name: "CLM-000201" })).toBeVisible();
  expect(screen.getByRole("link", { name: "CLM-000212" })).toBeVisible();
});
