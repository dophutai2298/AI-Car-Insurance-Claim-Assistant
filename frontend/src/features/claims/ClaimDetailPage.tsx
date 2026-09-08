import { ArrowLeft, CarFront, Document } from '@carbon/icons-react'
import { Alert, Button, Card, Chip, Skeleton } from '@heroui/react'
import { Link, useParams } from 'react-router'

import { lifecycleAction, statusLabel, statusTone } from './statusPresentation'
import { DamageAnalysisPanel } from './DamageAnalysisPanel'
import { EvidencePanel } from './EvidencePanel'
import { useClaim, useTransitionClaim } from './useClaims'

export function ClaimDetailPage() {
  const { claimId } = useParams()
  const { data: claim, error, isPending } = useClaim(claimId)
  const transition = useTransitionClaim(claimId)

  if (isPending) {
    return (
      <div className="mx-auto grid max-w-[1440px] gap-6 py-2">
        <div className="grid gap-6"><Skeleton className="h-10 w-40 rounded-lg" /><Skeleton className="h-72 rounded-lg" /></div>
      </div>
    )
  }

  if (error || !claim) {
    return (
      <div className="mx-auto max-w-[1440px] py-2">
          <Alert status="danger"><Alert.Title>Claim unavailable</Alert.Title><Alert.Description>The claim could not be loaded.</Alert.Description></Alert>
          <Link className="mt-6 inline-flex items-center gap-2 text-sm font-semibold text-blue-700" to="/claims"><ArrowLeft size={18} />Back to claims</Link>
      </div>
    )
  }

  return (
    <div className="mx-auto grid max-w-[1440px] gap-6 py-2">
        <Link className="flex w-fit items-center gap-2 text-sm font-semibold text-blue-700" to="/claims"><ArrowLeft size={18} />Back to claims</Link>
        <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-semibold text-slate-500">Claim case</p>
            <h1 className="mt-2 text-3xl font-semibold text-slate-950">Claim {claim.id}</h1>
            <p className="mt-2 text-sm text-slate-600">Created for {claim.claimant_name}</p>
          </div>
          <Chip color={statusTone[claim.status]} variant="soft">{statusLabel[claim.status]}</Chip>
        </header>

        <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
          <Card.Header className="flex items-center gap-3 border-b border-slate-100 px-6 py-5">
            <div className="flex size-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700 ring-1 ring-blue-100"><CarFront size={20} /></div>
            <div><Card.Title className="text-lg text-slate-950">Vehicle metadata</Card.Title><Card.Description className="text-sm text-slate-500">Case context for evidence intake and AI review.</Card.Description></div>
          </Card.Header>
          <Card.Content className="grid gap-5 p-6 sm:grid-cols-2">
            <DetailField label="Vehicle" value={`${claim.vehicle.make} ${claim.vehicle.model}`} />
            <DetailField label="Year" value={String(claim.vehicle.year)} />
            <DetailField label="License plate" value={claim.vehicle.license_plate ?? 'Not provided'} />
            <DetailField label="VIN" value={claim.vehicle.vin ?? 'Not provided'} />
          </Card.Content>
        </Card>

        <EvidencePanel claimId={claim.id} evidence={claim.evidence ?? []} />

        <DamageAnalysisPanel claim={claim} />

        {lifecycleAction[claim.status] ? (
          <section className="flex flex-col gap-4 border-y border-slate-200 bg-slate-50 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-semibold text-slate-950">Case workflow</p>
              <p className="mt-1 text-sm text-slate-600">Move this case through the AI review lifecycle.</p>
            </div>
            <Button
              isPending={transition.isPending}
              onPress={() => transition.mutate(lifecycleAction[claim.status]!.nextStatus)}
              variant="primary"
            >
              {lifecycleAction[claim.status]!.label}
            </Button>
          </section>
        ) : null}

        <Alert status="warning">
          <Document size={18} />
          <Alert.Title>AI review lifecycle</Alert.Title>
          <Alert.Description>Case status tracks the AI conclusion review only. It never represents final insurance claim approval or rejection.</Alert.Description>
        </Alert>
    </div>
  )
}

function DetailField({ label, value }: { label: string; value: string }) {
  return <div><div className="text-xs font-semibold uppercase text-slate-500">{label}</div><div className="mt-1 text-sm font-medium text-slate-950">{value}</div></div>
}
