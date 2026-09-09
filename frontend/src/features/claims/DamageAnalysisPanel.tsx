import { Analytics, Image, WarningAlt } from '@carbon/icons-react'
import { Alert, Button, Card, Chip } from '@heroui/react'

import { EvidenceImagePreview } from './EvidencePanel'
import { ClaimsApiError } from './claimsApi'
import { useDamageAnalysis } from './useClaims'
import type { ClaimDetail, DamageAssessment, DamageDetection } from './types'

const assessmentPresentation: Record<DamageAssessment, { label: string; color: 'default' | 'success' | 'warning' | 'danger' }> = {
  NO_DAMAGE: { label: 'No significant damage', color: 'default' },
  REPAIR_LIKELY: { label: 'Repair likely', color: 'success' },
  REPLACEMENT_LIKELY: { label: 'Replacement likely', color: 'danger' },
  MANUAL_INSPECTION_REQUIRED: { label: 'Manual inspection required', color: 'warning' },
}

export function DamageAnalysisPanel({ claim }: { claim: ClaimDetail }) {
  const damageAnalysis = useDamageAnalysis(claim.id)
  const evidence = claim.evidence ?? []
  const hasDamageImage = evidence.some((item) => item.category === 'VEHICLE_DAMAGE_IMAGE')
  const analysis = claim.latest_damage_analysis ?? null

  return (
    <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <Card.Header className="flex flex-col gap-4 border-b border-slate-100 px-6 py-5 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-lg bg-violet-50 text-violet-700 ring-1 ring-violet-100"><Analytics size={20} /></div>
          <div>
            <Card.Title className="text-lg text-slate-950">Damage analysis</Card.Title>
            <Card.Description className="text-sm text-slate-500">Normalized model findings for adjuster review.</Card.Description>
          </div>
        </div>
        <Button isDisabled={!hasDamageImage} isPending={damageAnalysis.isPending} onPress={() => damageAnalysis.mutate()} variant="primary">Run analysis</Button>
      </Card.Header>
      <Card.Content className="grid gap-5 p-6">
        {damageAnalysis.error ? (
          <Alert status="danger">
            <Alert.Title>Analysis could not run</Alert.Title>
            <Alert.Description>{damageAnalysis.error instanceof ClaimsApiError ? damageAnalysis.error.message : 'Unable to run damage analysis.'}</Alert.Description>
          </Alert>
        ) : null}
        {!hasDamageImage ? (
          <Alert status="warning">
            <WarningAlt size={18} />
            <Alert.Title>Vehicle damage image required</Alert.Title>
            <Alert.Description>Upload at least one vehicle damage image before running the analysis.</Alert.Description>
          </Alert>
        ) : null}
        {analysis ? <AnalysisResult assessment={analysis.assessment} detections={analysis.detections} rules={analysis.rules} warning={analysis.warning} /> : <p className="text-sm text-slate-500">No damage analysis has been run for this claim.</p>}
      </Card.Content>
    </Card>
  )
}

function AnalysisResult({ assessment, detections, rules, warning }: { assessment: DamageAssessment; detections: DamageDetection[]; rules: { confidence_threshold: number; repair_max_percentage: number; replacement_min_percentage: number } | null; warning: string | null }) {
  const presentation = assessmentPresentation[assessment]
  return (
    <div className="grid gap-5">
      <section className="flex flex-col gap-3 border-b border-slate-100 pb-5 sm:flex-row sm:items-center sm:justify-between">
        <div><p className="text-xs font-semibold uppercase text-slate-500">PoC assessment</p><p className="mt-1 text-base font-semibold text-slate-950">{presentation.label}</p></div>
        <Chip color={presentation.color} variant="soft">{presentation.label}</Chip>
      </section>
      {warning ? <Alert status="warning"><WarningAlt size={18} /><Alert.Title>Review note</Alert.Title><Alert.Description>{warning}</Alert.Description></Alert> : null}
      {rules ? <p className="text-xs text-slate-500">Rules used: confidence {formatPercentage(rules.confidence_threshold * 100)}, repair up to {formatPercentage(rules.repair_max_percentage)}, replacement from {formatPercentage(rules.replacement_min_percentage)}.</p> : null}
      {detections.length ? (
        <div className="grid gap-4">
          <h2 className="text-sm font-semibold text-slate-950">Detected damage</h2>
          <div className="grid gap-4 lg:grid-cols-2">{detections.map((detection, index) => <DetectionCard detection={detection} key={`${detection.annotated_evidence.id}-${index}`} />)}</div>
        </div>
      ) : (
        <div className="flex min-h-32 flex-col items-center justify-center gap-2 border border-dashed border-slate-300 bg-slate-50 px-5 text-center"><Image className="text-slate-400" size={24} /><p className="text-sm font-medium text-slate-700">No significant damage detections</p></div>
      )}
    </div>
  )
}

function DetectionCard({ detection }: { detection: DamageDetection }) {
  return (
    <article className="grid overflow-hidden border border-slate-200 sm:grid-cols-[10rem_minmax(0,1fr)]">
      <div className="flex min-h-36 items-center justify-center bg-slate-100"><EvidenceImagePreview item={detection.annotated_evidence} /></div>
      <div className="grid content-start gap-3 p-4">
        <div><p className="text-sm font-semibold text-slate-950">{formatLabel(detection.vehicle_part) || 'Vehicle area not identified'}</p><p className="mt-1 text-xs text-slate-500">{formatLabel(detection.damage_type) || 'Damage type not identified'}</p></div>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div><dt className="text-xs text-slate-500">Damage</dt><dd className="font-semibold text-slate-950">{formatPercentage(detection.damage_percentage)}</dd></div>
          <div><dt className="text-xs text-slate-500">Confidence</dt><dd className="font-semibold text-slate-950">{formatPercentage(detection.confidence * 100)}</dd></div>
          <div className="col-span-2"><dt className="text-xs text-slate-500">Image reference</dt><dd className="truncate font-medium text-slate-700">{detection.annotated_evidence.original_filename}</dd></div>
        </dl>
      </div>
    </article>
  )
}

function formatLabel(value: string | null) {
  return value?.replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function formatPercentage(value: number) {
  return `${Number.isInteger(value) ? value : value.toFixed(1)}%`
}
