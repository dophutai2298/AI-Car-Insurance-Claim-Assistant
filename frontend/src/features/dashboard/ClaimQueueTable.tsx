import { ChevronLeft, ChevronRight } from "@carbon/icons-react";
import { Button, Chip } from "@heroui/react";
import { flexRender, type PaginationState } from "@tanstack/react-table";
import {
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  type LegacyColumnDef,
  useLegacyTable,
} from "@tanstack/react-table/legacy";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";

import {
  DataTableToolbar,
  TableFilterSelect,
} from "../../components/DataTableToolbar";
import { statusLabel, statusTone } from "../claims/statusPresentation";
import type { ClaimStatus } from "../claims/types";
import type { ClaimQueueItem } from "./types";

type ClaimQueueTableProps = {
  claims: ClaimQueueItem[];
  emptyMessage?: string;
};

type DateRange = "ALL" | "TODAY" | "LAST_7_DAYS" | "LAST_30_DAYS";

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

export function ClaimQueueTable({
  claims,
  emptyMessage = "No claims match the selected filters.",
}: ClaimQueueTableProps) {
  const [globalFilter, setGlobalFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<ClaimStatus | "ALL">("ALL");
  const [dateRange, setDateRange] = useState<DateRange>("ALL");
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  });
  const dateFilteredClaims = useMemo(
    () =>
      claims.filter((claim) => isWithinDateRange(claim.updatedAt, dateRange)),
    [claims, dateRange],
  );
  const columns = useMemo<LegacyColumnDef<ClaimQueueItem>[]>(
    () => [
      {
        accessorKey: "id",
        header: "Claim",
        cell: ({ row }) => (
          <div>
            <Link
              className="font-semibold text-blue-700 hover:text-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
              to={`/claims/${row.original.id}`}
            >
              {row.original.id}
            </Link>
            <div className="mt-0.5 text-xs text-slate-500">
              {row.original.claimant}
            </div>
          </div>
        ),
      },
      {
        accessorKey: "vehicle",
        header: "Vehicle",
      },
      {
        accessorKey: "status",
        header: "Review status",
        cell: ({ row }) => (
          <Chip
            color={statusTone[row.original.status]}
            size="sm"
            variant="soft"
          >
            {statusLabel[row.original.status]}
          </Chip>
        ),
      },
      {
        accessorKey: "updatedAt",
        header: "Last updated",
        cell: ({ row }) => formatDateTime(row.original.updatedAt),
      },
    ],
    [],
  );
  const table = useLegacyTable({
    data: dateFilteredClaims,
    columns,
    state: {
      globalFilter,
      columnFilters:
        statusFilter === "ALL" ? [] : [{ id: "status", value: statusFilter }],
      pagination,
    },
    onGlobalFilterChange: setGlobalFilter,
    globalFilterFn: "includesString",
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });
  const rows = table.getRowModel().rows;
  const totalRows = table.getFilteredRowModel().rows.length;
  const firstVisibleRow = totalRows
    ? pagination.pageIndex * pagination.pageSize + 1
    : 0;
  const lastVisibleRow = Math.min(
    (pagination.pageIndex + 1) * pagination.pageSize,
    totalRows,
  );
  const pageCount = table.getPageCount();
  const isFiltered =
    Boolean(globalFilter) || statusFilter !== "ALL" || dateRange !== "ALL";
  const canGoToPreviousPage = pagination.pageIndex > 0;
  const canGoToNextPage = pagination.pageIndex < pageCount - 1;

  useEffect(() => {
    setPagination((current) => ({ ...current, pageIndex: 0 }));
  }, [globalFilter, statusFilter, dateRange]);

  return (
    <div className="grid gap-4">
      <DataTableToolbar
        clearLabel="Clear filters"
        isFiltered={isFiltered}
        onClear={() => {
          setGlobalFilter("");
          setStatusFilter("ALL");
          setDateRange("ALL");
        }}
        onSearchChange={setGlobalFilter}
        resultCount={rows.length}
        resultLabel={rows.length === 1 ? "claim shown" : "claims shown"}
        searchLabel="Search claims"
        searchPlaceholder="Claim number, claimant, or vehicle"
        searchValue={globalFilter}
      >
        <TableFilterSelect
          label="Status"
          onChange={(value) => setStatusFilter(value as ClaimStatus | "ALL")}
          options={[
            { label: "All statuses", value: "ALL" },
            ...Object.entries(statusLabel).map(([value, label]) => ({
              label,
              value,
            })),
          ]}
          value={statusFilter}
        />
        <TableFilterSelect
          label="Updated"
          onChange={(value) => setDateRange(value as DateRange)}
          options={[
            { label: "All dates", value: "ALL" },
            { label: "Today", value: "TODAY" },
            { label: "Last 7 days", value: "LAST_7_DAYS" },
            { label: "Last 30 days", value: "LAST_30_DAYS" },
          ]}
          value={dateRange}
        />
      </DataTableToolbar>

      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="w-full min-w-[44rem] border-collapse text-left text-sm">
          <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-500">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th className="px-4 py-3" key={header.id} scope="col">
                    {header.isPlaceholder
                      ? null
                      : flexRender(
                          header.column.columnDef.header,
                          header.getContext(),
                        )}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {rows.map((row) => (
              <tr className="transition-colors hover:bg-slate-50" key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <td className="px-4 py-4 text-slate-700" key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
            {rows.length === 0 ? (
              <tr>
                <td
                  className="px-4 py-10 text-center text-sm text-slate-500"
                  colSpan={columns.length}
                >
                  {emptyMessage}
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-3 border-t border-slate-100 pt-4 sm:flex-row sm:items-end sm:justify-between">
        <p className="text-sm tabular-nums text-slate-600">
          {totalRows
            ? `Showing ${firstVisibleRow}-${lastVisibleRow} of ${totalRows} claims`
            : "No claims to show"}
        </p>
        <div className="flex flex-wrap items-end gap-2">
          <TableFilterSelect
            label="Rows per page"
            onChange={(value) =>
              setPagination({ pageIndex: 0, pageSize: Number(value) })
            }
            options={[10, 20, 50, 100].map((pageSize) => ({
              label: String(pageSize),
              value: String(pageSize),
            }))}
            value={String(pagination.pageSize)}
          />
          <div className="flex items-center gap-1 pb-0.5">
            <Button
              aria-label="Previous page"
              isDisabled={!canGoToPreviousPage}
              onPress={() =>
                setPagination((current) => ({
                  ...current,
                  pageIndex: Math.max(0, current.pageIndex - 1),
                }))
              }
              size="sm"
              variant="ghost"
            >
              <ChevronLeft size={18} />
            </Button>
            <span className="min-w-24 px-2 text-center text-sm font-medium tabular-nums text-slate-700">
              Page {totalRows ? pagination.pageIndex + 1 : 0} of {pageCount}
            </span>
            <Button
              aria-label="Next page"
              isDisabled={!canGoToNextPage}
              onPress={() =>
                setPagination((current) => ({
                  ...current,
                  pageIndex: Math.min(pageCount - 1, current.pageIndex + 1),
                }))
              }
              size="sm"
              variant="ghost"
            >
              <ChevronRight size={18} />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

function formatDateTime(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : dateFormatter.format(date);
}

function isWithinDateRange(value: string, range: DateRange) {
  if (range === "ALL") return true;

  const updatedAt = new Date(value);
  if (Number.isNaN(updatedAt.getTime())) return false;

  const now = new Date();
  if (range === "TODAY") return updatedAt.toDateString() === now.toDateString();

  const days = range === "LAST_7_DAYS" ? 7 : 30;
  const cutoff = new Date(now);
  cutoff.setDate(now.getDate() - days);
  return updatedAt >= cutoff && updatedAt <= now;
}
