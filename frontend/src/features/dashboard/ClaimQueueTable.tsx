import {
  ChevronLeft,
  ChevronRight,
  ChevronSort,
  ChevronSortDown,
  ChevronSortUp,
} from "@carbon/icons-react";
import { Button, Chip } from "@heroui/react";
import {
  flexRender,
  type PaginationState,
  type SortingState,
} from "@tanstack/react-table";
import {
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  type LegacyColumnDef,
  useLegacyTable,
} from "@tanstack/react-table/legacy";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";

import {
  DataTableToolbar,
  TableFilterSelect,
} from "../../components/DataTableToolbar";
import { statusTone } from "../claims/statusPresentation";
import type { ClaimStatus } from "../claims/types";
import type { ClaimQueueItem } from "./types";

type ClaimQueueTableProps = {
  claims: ClaimQueueItem[];
  emptyMessage?: string;
};

type DateRange = "ALL" | "TODAY" | "LAST_7_DAYS" | "LAST_30_DAYS";

export function ClaimQueueTable({
  claims,
  emptyMessage,
}: ClaimQueueTableProps) {
  const { i18n, t } = useTranslation();
  const [globalFilter, setGlobalFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<ClaimStatus | "ALL">("ALL");
  const [dateRange, setDateRange] = useState<DateRange>("ALL");
  const [pagination, setPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  });
  const [sorting, setSorting] = useState<SortingState>([]);
  const dateFilteredClaims = useMemo(
    () =>
      claims.filter((claim) => isWithinDateRange(claim.updatedAt, dateRange)),
    [claims, dateRange],
  );
  const columns = useMemo<LegacyColumnDef<ClaimQueueItem>[]>(
    () => [
      {
        accessorKey: "id",
        header: t("queue.claim"),
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
        header: t("queue.vehicle"),
      },
      {
        accessorKey: "status",
        header: t("queue.reviewStatus"),
        cell: ({ row }) => (
          <Chip
            color={statusTone[row.original.status]}
            size="sm"
            variant="soft"
          >
            {t(`claim.status.${row.original.status}`)}
          </Chip>
        ),
      },
      {
        accessorKey: "updatedAt",
        header: t("queue.lastUpdated"),
        cell: ({ row }) =>
          formatDateTime(row.original.updatedAt, i18n.language),
      },
    ],
    [i18n.language, t],
  );
  const table = useLegacyTable({
    data: dateFilteredClaims,
    columns,
    state: {
      globalFilter,
      columnFilters:
        statusFilter === "ALL" ? [] : [{ id: "status", value: statusFilter }],
      pagination,
      sorting,
    },
    onGlobalFilterChange: setGlobalFilter,
    onSortingChange: setSorting,
    globalFilterFn: "includesString",
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    enableSortingRemoval: false,
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
  }, [globalFilter, statusFilter, dateRange, sorting]);

  return (
    <div className="grid gap-4">
      <DataTableToolbar
        clearLabel={t("queue.clearFilters")}
        isFiltered={isFiltered}
        onClear={() => {
          setGlobalFilter("");
          setStatusFilter("ALL");
          setDateRange("ALL");
        }}
        onSearchChange={setGlobalFilter}
        resultCount={rows.length}
        resultLabel={
          rows.length === 1 ? t("queue.claimShown") : t("queue.claimsShown")
        }
        searchLabel={t("queue.searchLabel")}
        searchPlaceholder={t("queue.searchPlaceholder")}
        searchValue={globalFilter}
      >
        <TableFilterSelect
          label={t("queue.status")}
          onChange={(value) => setStatusFilter(value as ClaimStatus | "ALL")}
          options={[
            { label: t("queue.allStatuses"), value: "ALL" },
            ...(Object.keys(statusTone) as ClaimStatus[]).map((value) => ({
              label: t(`claim.status.${value}`),
              value,
            })),
          ]}
          value={statusFilter}
        />
        <TableFilterSelect
          label={t("queue.updated")}
          onChange={(value) => setDateRange(value as DateRange)}
          options={[
            { label: t("queue.allDates"), value: "ALL" },
            { label: t("queue.today"), value: "TODAY" },
            { label: t("queue.last7Days"), value: "LAST_7_DAYS" },
            { label: t("queue.last30Days"), value: "LAST_30_DAYS" },
          ]}
          value={dateRange}
        />
      </DataTableToolbar>

      <div className="overflow-x-auto rounded-lg border border-slate-200">
        <table className="w-full min-w-[44rem] border-collapse text-left text-sm">
          <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-500">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  const direction = header.column.getIsSorted();
                  const label = header.isPlaceholder
                    ? ""
                    : String(
                        header.column.columnDef.header ?? header.column.id,
                      );
                  const Icon =
                    direction === "asc"
                      ? ChevronSortUp
                      : direction === "desc"
                        ? ChevronSortDown
                        : ChevronSort;
                  return (
                    <th
                      aria-sort={
                        direction === "asc"
                          ? "ascending"
                          : direction === "desc"
                            ? "descending"
                            : "none"
                      }
                      className="px-4 py-3"
                      key={header.id}
                      scope="col"
                    >
                      {header.isPlaceholder ? null : (
                        <button
                          aria-label={t(
                            direction === "asc"
                              ? "queue.sortDescending"
                              : "queue.sortAscending",
                            { column: label },
                          )}
                          className="inline-flex items-center gap-1 text-left hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
                          onClick={header.column.getToggleSortingHandler()}
                          type="button"
                        >
                          {flexRender(
                            header.column.columnDef.header,
                            header.getContext(),
                          )}
                          <Icon aria-hidden="true" size={16} />
                        </button>
                      )}
                    </th>
                  );
                })}
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
                  {emptyMessage ?? t("queue.empty")}
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      <div className="flex flex-col gap-3 border-t border-slate-100 pt-4 sm:flex-row sm:items-end sm:justify-between">
        <p className="text-sm tabular-nums text-slate-600">
          {totalRows
            ? t("queue.showing", {
                first: firstVisibleRow,
                last: lastVisibleRow,
                total: totalRows,
              })
            : t("queue.none")}
        </p>
        <div className="flex flex-wrap items-end gap-2">
          <TableFilterSelect
            label={t("queue.rowsPerPage")}
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
              aria-label={t("queue.previousPage")}
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
              {t("queue.page", {
                current: totalRows ? pagination.pageIndex + 1 : 0,
                total: pageCount,
              })}
            </span>
            <Button
              aria-label={t("queue.nextPage")}
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

function formatDateTime(value: string, locale: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
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
