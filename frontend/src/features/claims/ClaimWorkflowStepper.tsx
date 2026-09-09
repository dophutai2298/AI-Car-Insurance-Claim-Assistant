import { CheckmarkOutline, WarningAlt } from '@carbon/icons-react'
import { useTranslation } from 'react-i18next'

import type { ClaimStatus } from './types'

export type ClaimStepState = 'completed' | 'current' | 'available' | 'blocked' | 'warning'

const stateStyles: Record<ClaimStepState, string> = {
  completed: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  current: 'border-blue-300 bg-blue-50 text-blue-800',
  available: 'border-slate-300 bg-white text-slate-700',
  blocked: 'border-slate-200 bg-slate-50 text-slate-400',
  warning: 'border-amber-300 bg-amber-50 text-amber-800',
}

const stateLabels: Record<ClaimStepState, string> = {
  completed: 'claim.completed', current: 'claim.current', available: 'claim.available', blocked: 'claim.blocked', warning: 'claim.warning',
}

type ClaimStepId = 'information' | 'evidence' | 'analysis' | 'aiReview' | 'humanReview'

export function ClaimWorkflowStepper({
  current = 'information',
  states,
}: {
  current?: ClaimStepId
  states?: Partial<Record<ClaimStepId, ClaimStepState>>
}) {
  const { t } = useTranslation()
  const steps = [
    { id: 'information', label: t('claim.information') },
    { id: 'evidence', label: t('claim.stepEvidence') },
    { id: 'analysis', label: t('claim.stepAnalysis') },
    { id: 'aiReview', label: t('claim.stepAiReview') },
    { id: 'humanReview', label: t('claim.stepHumanReview') },
  ] as const
  const currentIndex = steps.findIndex((step) => step.id === current)

  return <ol aria-label={t('claim.workflow')} className="grid gap-2 md:grid-cols-5">{steps.map((step, index) => {
    const state: ClaimStepState = states?.[step.id] ?? (index < currentIndex ? 'completed' : index === currentIndex ? 'current' : 'blocked')
    return <li className={`flex min-h-16 items-center gap-3 border px-3 py-2 ${stateStyles[state]}`} key={step.id}>
      <span className="flex size-7 shrink-0 items-center justify-center border border-current text-xs font-semibold">{state === 'completed' ? <CheckmarkOutline size={16} /> : state === 'warning' ? <WarningAlt size={16} /> : index + 1}</span>
      <span className="min-w-0"><span className="block text-sm font-semibold">{step.label}</span><span className="block text-xs opacity-80">{t(stateLabels[state])}</span></span>
    </li>
  })}</ol>
}

export function claimWorkflowForStatus(status: ClaimStatus) {
  const completedInformation = { information: 'completed' as const }
  const completedEvidence = { ...completedInformation, evidence: 'completed' as const }
  const completedAnalysis = { ...completedEvidence, analysis: 'completed' as const }

  if (status === 'DRAFT') return { current: 'evidence' as const, states: { ...completedInformation, evidence: 'current' as const } }
  if (status === 'ANALYZING') return { current: 'analysis' as const, states: { ...completedEvidence, analysis: 'current' as const } }
  if (status === 'REVIEW_REQUIRED' || status === 'FAILED') return { current: 'humanReview' as const, states: { ...completedAnalysis, aiReview: 'warning' as const, humanReview: 'current' as const } }
  return { current: 'humanReview' as const, states: { ...completedAnalysis, aiReview: 'completed' as const, humanReview: 'completed' as const } }
}
