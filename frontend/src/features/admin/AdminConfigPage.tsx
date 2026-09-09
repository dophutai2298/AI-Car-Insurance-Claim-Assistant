import { CheckmarkOutline, SettingsAdjust, Time } from '@carbon/icons-react'
import { Alert, Button, Card, Chip, Input, Label, Skeleton, TextField } from '@heroui/react'
import { useEffect, useState, type FormEvent } from 'react'

import { AdminApiError } from './adminApi'
import { useAssessmentRuleHistory, useAssessmentRules, useUpdateAssessmentRules } from './useAssessmentRules'
import { VehicleManufacturerPanel } from './VehicleManufacturerPanel'

type RuleForm = {
  confidenceThreshold: string
  repairMaxPercentage: string
  replacementMinPercentage: string
}

export function AdminConfigPage() {
  const rules = useAssessmentRules()
  const history = useAssessmentRuleHistory()
  const updateRules = useUpdateAssessmentRules()
  const [form, setForm] = useState<RuleForm>({ confidenceThreshold: '', repairMaxPercentage: '', replacementMinPercentage: '' })
  const [error, setError] = useState('')

  useEffect(() => {
    if (!rules.data) return
    setForm({
      confidenceThreshold: String(rules.data.values.confidence_threshold),
      repairMaxPercentage: String(rules.data.values.repair_max_percentage),
      replacementMinPercentage: String(rules.data.values.replacement_min_percentage),
    })
  }, [rules.data])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    const values = {
      confidence_threshold: Number(form.confidenceThreshold),
      repair_max_percentage: Number(form.repairMaxPercentage),
      replacement_min_percentage: Number(form.replacementMinPercentage),
    }
    if (!Number.isFinite(values.confidence_threshold) || values.confidence_threshold < 0 || values.confidence_threshold > 1) {
      setError('Confidence threshold must be between 0 and 1.')
      return
    }
    if (!Number.isFinite(values.repair_max_percentage) || !Number.isFinite(values.replacement_min_percentage) || values.repair_max_percentage < 0 || values.repair_max_percentage > 100 || values.replacement_min_percentage < 0 || values.replacement_min_percentage > 100) {
      setError('Damage thresholds must be between 0 and 100.')
      return
    }
    if (values.repair_max_percentage >= values.replacement_min_percentage) {
      setError('Repair maximum must be lower than the replacement minimum.')
      return
    }
    try {
      await updateRules.mutateAsync(values)
    } catch (caughtError) {
      setError(caughtError instanceof AdminApiError ? caughtError.message : 'Unable to update assessment rules.')
    }
  }

  return (
    <div className="mx-auto grid max-w-[1120px] gap-6 py-2">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-500">Administration</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-950">Assessment rules</h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">Global PoC rules applied to new vehicle damage analyses.</p>
        </div>
        <Chip color="default" variant="soft">Global configuration</Chip>
      </header>

      <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <Card.Header className="flex items-center gap-3 border-b border-slate-100 px-6 py-5">
          <div className="flex size-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700 ring-1 ring-blue-100"><SettingsAdjust size={20} /></div>
          <div><Card.Title className="text-lg text-slate-950">Active thresholds</Card.Title><Card.Description className="text-sm text-slate-500">Changes apply only to analyses started after the update.</Card.Description></div>
        </Card.Header>
        <Card.Content className="p-6">
          {rules.isPending ? <RuleFormSkeleton /> : null}
          {rules.error ? <Alert status="danger"><Alert.Title>Configuration unavailable</Alert.Title><Alert.Description>Assessment rules could not be loaded.</Alert.Description></Alert> : null}
          {rules.data ? (
            <form className="grid gap-5" onSubmit={submit}>
              {error ? <Alert status="danger"><Alert.Title>Rules were not saved</Alert.Title><Alert.Description>{error}</Alert.Description></Alert> : null}
              <div className="grid gap-5 md:grid-cols-3">
                <RuleField label="Confidence threshold" name="confidence-threshold" hint="0 to 1" value={form.confidenceThreshold} onChange={(confidenceThreshold) => setForm((current) => ({ ...current, confidenceThreshold }))} />
                <RuleField label="Repair maximum" name="repair-maximum" hint="Damage percentage" value={form.repairMaxPercentage} onChange={(repairMaxPercentage) => setForm((current) => ({ ...current, repairMaxPercentage }))} />
                <RuleField label="Replacement minimum" name="replacement-minimum" hint="Damage percentage" value={form.replacementMinPercentage} onChange={(replacementMinPercentage) => setForm((current) => ({ ...current, replacementMinPercentage }))} />
              </div>
              <div className="flex flex-col gap-3 border-t border-slate-100 pt-5 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-xs text-slate-500">Last changed by {rules.data.updated_by ?? 'system defaults'} on {formatDate(rules.data.updated_at)}</p>
                <Button isPending={updateRules.isPending} type="submit" variant="primary"><CheckmarkOutline size={18} />Save rules</Button>
              </div>
            </form>
          ) : null}
        </Card.Content>
      </Card>

      <VehicleManufacturerPanel />

      <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
        <Card.Header className="flex items-center gap-3 border-b border-slate-100 px-6 py-5"><Time className="text-slate-600" size={20} /><div><Card.Title className="text-lg text-slate-950">Change history</Card.Title><Card.Description className="text-sm text-slate-500">Persisted audit trail for assessment-rule updates.</Card.Description></div></Card.Header>
        <Card.Content className="p-6">
          {history.isPending ? <Skeleton className="h-20 rounded-lg" /> : null}
          {history.error ? <Alert status="warning"><Alert.Title>History unavailable</Alert.Title><Alert.Description>The active rules are unaffected.</Alert.Description></Alert> : null}
          {history.data?.length ? <div className="divide-y divide-slate-100">{history.data.map((change) => <HistoryRow change={change} key={`${change.changed_at}-${change.changed_by}`} />)}</div> : null}
          {history.data && history.data.length === 0 ? <p className="text-sm text-slate-500">No administrator changes have been recorded.</p> : null}
        </Card.Content>
      </Card>
    </div>
  )
}

function RuleField({ hint, label, name, onChange, value }: { hint: string; label: string; name: string; onChange: (value: string) => void; value: string }) {
  return <TextField fullWidth isRequired name={name} type="number"><Label>{label}</Label><Input inputMode="decimal" onChange={(event) => onChange(event.target.value)} value={value} /><p className="mt-1 text-xs text-slate-500">{hint}</p></TextField>
}

function HistoryRow({ change }: { change: { changed_by: string; changed_at: string; old_values: { confidence_threshold: number; repair_max_percentage: number; replacement_min_percentage: number }; new_values: { confidence_threshold: number; repair_max_percentage: number; replacement_min_percentage: number } } }) {
  return <article className="grid gap-3 py-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center"><div><p className="text-sm font-semibold text-slate-950">{change.changed_by}</p><p className="mt-1 text-xs text-slate-500">Confidence {change.old_values.confidence_threshold} to {change.new_values.confidence_threshold}; repair {change.old_values.repair_max_percentage}% to {change.new_values.repair_max_percentage}%; replacement {change.old_values.replacement_min_percentage}% to {change.new_values.replacement_min_percentage}%.</p></div><time className="text-xs text-slate-500">{formatDate(change.changed_at)}</time></article>
}

function RuleFormSkeleton() {
  return <div className="grid gap-5"><div className="grid gap-5 md:grid-cols-3"><Skeleton className="h-16 rounded-lg" /><Skeleton className="h-16 rounded-lg" /><Skeleton className="h-16 rounded-lg" /></div><Skeleton className="h-10 w-28 self-end rounded-lg" /></div>
}

function formatDate(value: string) {
  return new Date(value).toLocaleString()
}
