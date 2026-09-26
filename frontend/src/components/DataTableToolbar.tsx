import { Reset } from "@carbon/icons-react";
import { Button, Input, Label, TextField } from "@heroui/react";
import type { ReactNode } from "react";

type DataTableToolbarProps = {
  searchLabel: string;
  searchPlaceholder: string;
  searchValue: string;
  onSearchChange: (value: string) => void;
  resultCount: number;
  resultLabel: string;
  isFiltered: boolean;
  onClear: () => void;
  clearLabel: string;
  children?: ReactNode;
};

export function DataTableToolbar({
  searchLabel,
  searchPlaceholder,
  searchValue,
  onSearchChange,
  resultCount,
  resultLabel,
  isFiltered,
  onClear,
  clearLabel,
  children,
}: DataTableToolbarProps) {
  return (
    <div className="grid gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3 lg:grid-cols-[minmax(15rem,1fr)_auto] lg:items-end">
      <TextField fullWidth name={`${searchLabel}-search`}>
        <Label>{searchLabel}</Label>
        <Input
          onChange={(event) => onSearchChange(event.target.value)}
          placeholder={searchPlaceholder}
          value={searchValue}
        />
      </TextField>
      <div className="flex flex-wrap items-end gap-2">
        {children}
        <Button
          isDisabled={!isFiltered}
          onPress={onClear}
          size="sm"
          variant="ghost"
        >
          <Reset size={16} />
          {clearLabel}
        </Button>
      </div>
      <p className="text-xs font-medium tabular-nums text-slate-500 lg:col-span-2">
        {resultCount} {resultLabel}
      </p>
    </div>
  );
}

export function TableFilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: Array<{ label: string; value: string }>;
  onChange: (value: string) => void;
}) {
  return (
    <label className="grid gap-1 text-xs font-semibold text-slate-600">
      {label}
      <select
        className="h-10 min-w-36 rounded-lg border border-slate-300 bg-white px-3 text-sm font-normal text-slate-800 outline-none transition-colors focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
        onChange={(event) => onChange(event.target.value)}
        value={value}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}
