import { Chip } from '@heroui/react'
import { flexRender } from '@tanstack/react-table'
import {
  getCoreRowModel,
  type LegacyColumnDef,
  useLegacyTable,
} from '@tanstack/react-table/legacy'
import { useMemo } from 'react'

import type { ClaimQueueItem, ClaimStatus } from './types'

const statusTone: Record<ClaimStatus, 'default' | 'accent' | 'success' | 'warning' | 'danger'> = {
  DRAFT: 'default',
  ANALYZING: 'accent',
  REVIEW_REQUIRED: 'warning',
  AI_APPROVED: 'success',
  AI_REJECTED: 'danger',
  FAILED: 'danger',
}

const statusLabel: Record<ClaimStatus, string> = {
  DRAFT: 'Draft',
  ANALYZING: 'Analyzing',
  REVIEW_REQUIRED: 'Review required',
  AI_APPROVED: 'AI approved',
  AI_REJECTED: 'AI rejected',
  FAILED: 'Failed',
}

type ClaimQueueTableProps = {
  claims: ClaimQueueItem[]
}

export function ClaimQueueTable({ claims }: ClaimQueueTableProps) {
  const columns = useMemo<LegacyColumnDef<ClaimQueueItem>[]>(
    () => [
      {
        accessorKey: 'id',
        header: 'Claim',
        cell: ({ row }) => (
          <div>
            <div className="font-semibold text-slate-950">{row.original.id}</div>
            <div className="text-xs text-slate-500">{row.original.claimant}</div>
          </div>
        ),
      },
      {
        accessorKey: 'vehicle',
        header: 'Vehicle',
      },
      {
        accessorKey: 'status',
        header: 'Status',
        cell: ({ row }) => (
          <Chip color={statusTone[row.original.status]} size="sm" variant="soft">
            {statusLabel[row.original.status]}
          </Chip>
        ),
      },
      {
        accessorKey: 'assessment',
        header: 'Assessment',
      },
      {
        accessorKey: 'evidenceCount',
        header: 'Evidence',
        cell: ({ row }) => `${row.original.evidenceCount} files`,
      },
      {
        accessorKey: 'updatedAt',
        header: 'Updated',
      },
    ],
    [],
  )

  const table = useLegacyTable({
    data: claims,
    columns,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
      <div className="overflow-x-hidden">
        <table className="w-full table-fixed border-collapse text-left text-sm">
          <thead className="bg-slate-50 text-xs font-semibold uppercase text-slate-500">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <th className="px-4 py-3 break-words" key={header.id}>
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody className="divide-y divide-slate-100">
            {table.getRowModel().rows.map((row) => (
              <tr className="hover:bg-slate-50" key={row.id}>
                {row.getVisibleCells().map((cell) => (
                  <td className="break-words px-4 py-4 text-slate-700" key={cell.id}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
