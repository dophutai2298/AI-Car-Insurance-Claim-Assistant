import { CheckmarkOutline, SettingsAdjust, Time } from "@carbon/icons-react";
import {
  Alert,
  Button,
  Card,
  Chip,
  Input,
  Label,
  Skeleton,
  TextField,
} from "@heroui/react";
import { useEffect, useState, type FormEvent } from "react";
import { useTranslation } from "react-i18next";

import { AdminApiError } from "./adminApi";
import {
  useAssessmentRuleHistory,
  useAssessmentRules,
  useUpdateAssessmentRules,
} from "./useAssessmentRules";
import { VehicleManufacturerPanel } from "./VehicleManufacturerPanel";

type RuleForm = {
  repairMaxPercentage: string;
  replacementMinPercentage: string;
};

export function AdminConfigPage() {
  const rules = useAssessmentRules();
  const history = useAssessmentRuleHistory();
  const updateRules = useUpdateAssessmentRules();
  const { i18n, t } = useTranslation();
  const [form, setForm] = useState<RuleForm>({
    repairMaxPercentage: "",
    replacementMinPercentage: "",
  });
  const [error, setError] = useState("");

  useEffect(() => {
    if (!rules.data) return;
    setForm({
      repairMaxPercentage: String(rules.data.values.repair_max_percentage),
      replacementMinPercentage: String(
        rules.data.values.replacement_min_percentage,
      ),
    });
  }, [rules.data]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const values = {
      repair_max_percentage: Number(form.repairMaxPercentage),
      replacement_min_percentage: Number(form.replacementMinPercentage),
    };
    if (
      !Number.isFinite(values.repair_max_percentage) ||
      !Number.isFinite(values.replacement_min_percentage) ||
      values.repair_max_percentage < 0 ||
      values.repair_max_percentage > 100 ||
      values.replacement_min_percentage < 0 ||
      values.replacement_min_percentage > 100
    ) {
      setError(t("admin.thresholdRangeError"));
      return;
    }
    if (values.repair_max_percentage >= values.replacement_min_percentage) {
      setError(t("admin.thresholdOrderError"));
      return;
    }
    try {
      await updateRules.mutateAsync(values);
    } catch (caughtError) {
      setError(
        caughtError instanceof AdminApiError
          ? caughtError.message
          : t("admin.updateFailed"),
      );
    }
  }

  return (
    <div className="mx-auto grid max-w-[1440px] gap-6">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-500">
            {t("admin.eyebrow")}
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">
            {t("admin.title")}
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            {t("admin.description")}
          </p>
        </div>
        <Chip color="default" variant="soft">
          {t("admin.globalConfiguration")}
        </Chip>
      </header>

      <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <Card.Header className="flex items-left gap-3 border-b border-slate-100 px-6 py-5">
          {/* <div className="flex size-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700 ring-1 ring-blue-100">
            <SettingsAdjust size={20} />
          </div> */}
          <div>
            <Card.Title className="text-lg text-slate-950">
              {t("admin.activeThresholds")}
            </Card.Title>
            <Card.Description className="text-sm text-slate-500">
              {t("admin.thresholdDescription")}
            </Card.Description>
          </div>
        </Card.Header>
        <Card.Content className="p-6">
          {rules.isPending ? <RuleFormSkeleton /> : null}
          {rules.error ? (
            <Alert status="danger">
              <Alert.Title>{t("admin.configurationUnavailable")}</Alert.Title>
              <Alert.Description>
                {t("admin.configurationLoadFailed")}
              </Alert.Description>
            </Alert>
          ) : null}
          {rules.data ? (
            <form className="grid gap-5" onSubmit={submit}>
              {error ? (
                <Alert status="danger">
                  <Alert.Title>{t("admin.rulesNotSaved")}</Alert.Title>
                  <Alert.Description>{error}</Alert.Description>
                </Alert>
              ) : null}
              <div className="grid gap-5 md:grid-cols-2">
                <RuleField
                  label={t("admin.repairMaximum")}
                  name="repair-maximum"
                  hint={t("admin.damagePercentage")}
                  value={form.repairMaxPercentage}
                  onChange={(repairMaxPercentage) =>
                    setForm((current) => ({ ...current, repairMaxPercentage }))
                  }
                />
                <RuleField
                  label={t("admin.replacementMinimum")}
                  name="replacement-minimum"
                  hint={t("admin.damagePercentage")}
                  value={form.replacementMinPercentage}
                  onChange={(replacementMinPercentage) =>
                    setForm((current) => ({
                      ...current,
                      replacementMinPercentage,
                    }))
                  }
                />
              </div>
              <div className="flex flex-col gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs text-slate-500">
                  {t("admin.lastChanged", {
                    user: rules.data.updated_by ?? t("admin.systemDefaults"),
                    date: formatDate(rules.data.updated_at, i18n.language),
                  })}
                </p>
                <Button
                  isPending={updateRules.isPending}
                  type="submit"
                  variant="primary"
                >
                  <CheckmarkOutline size={18} />
                  {t("admin.saveRules")}
                </Button>
              </div>
            </form>
          ) : null}
        </Card.Content>
      </Card>

      <VehicleManufacturerPanel />

      <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <Card.Header className="flex items-center gap-3 border-b border-slate-100 px-6 py-5">
          <Time className="text-slate-600" size={20} />
          <div>
            <Card.Title className="text-lg text-slate-950">
              {t("admin.changeHistory")}
            </Card.Title>
            <Card.Description className="text-sm text-slate-500">
              {t("admin.historyDescription")}
            </Card.Description>
          </div>
        </Card.Header>
        <Card.Content className="p-6">
          {history.isPending ? <Skeleton className="h-20 rounded-lg" /> : null}
          {history.error ? (
            <Alert status="warning">
              <Alert.Title>{t("admin.historyUnavailable")}</Alert.Title>
              <Alert.Description>
                {t("admin.activeRulesUnaffected")}
              </Alert.Description>
            </Alert>
          ) : null}
          {history.data?.length ? (
            <div className="divide-y divide-slate-100">
              {history.data.map((change) => (
                <HistoryRow
                  change={change}
                  key={`${change.changed_at}-${change.changed_by}`}
                />
              ))}
            </div>
          ) : null}
          {history.data && history.data.length === 0 ? (
            <p className="text-sm text-slate-500">{t("admin.noHistory")}</p>
          ) : null}
        </Card.Content>
      </Card>
    </div>
  );
}

function RuleField({
  hint,
  label,
  name,
  onChange,
  value,
}: {
  hint: string;
  label: string;
  name: string;
  onChange: (value: string) => void;
  value: string;
}) {
  return (
    <TextField fullWidth isRequired name={name} type="number">
      <Label>{label}</Label>
      <Input
        inputMode="decimal"
        onChange={(event) => onChange(event.target.value)}
        value={value}
      />
      <p className="mt-1 text-xs text-slate-500">{hint}</p>
    </TextField>
  );
}

function HistoryRow({
  change,
}: {
  change: {
    changed_by: string;
    changed_at: string;
    old_values: {
      repair_max_percentage: number;
      replacement_min_percentage: number;
    };
    new_values: {
      repair_max_percentage: number;
      replacement_min_percentage: number;
    };
  };
}) {
  const { i18n, t } = useTranslation();

  return (
    <article className="grid gap-3 py-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
      <div>
        <p className="text-sm font-semibold text-slate-950">
          {change.changed_by}
        </p>
        <p className="mt-1 text-xs text-slate-500">
          {t("admin.historyChange", {
            oldRepair: change.old_values.repair_max_percentage,
            newRepair: change.new_values.repair_max_percentage,
            oldReplacement: change.old_values.replacement_min_percentage,
            newReplacement: change.new_values.replacement_min_percentage,
          })}
        </p>
      </div>
      <time className="text-xs text-slate-500">
        {formatDate(change.changed_at, i18n.language)}
      </time>
    </article>
  );
}

function RuleFormSkeleton() {
  return (
    <div className="grid gap-5">
      <div className="grid gap-5 md:grid-cols-2">
        <Skeleton className="h-16 rounded-lg" />
        <Skeleton className="h-16 rounded-lg" />
      </div>
      <Skeleton className="h-10 w-28 self-end rounded-lg" />
    </div>
  );
}

function formatDate(value: string, locale: string) {
  return new Date(value).toLocaleString(locale);
}
