import {
  Activity,
  Ai,
  ChartColumn,
  CheckmarkOutline,
  ChevronRight,
  CloudUpload,
  Document,
  ErrorOutline,
  Login,
  SettingsAdjust,
  WarningAlt,
} from '@carbon/icons-react'
import { Alert, Button, Card, Chip, EmptyState, Skeleton } from '@heroui/react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { ClaimQueueTable } from './features/dashboard/ClaimQueueTable'
import type { CapabilityState } from './features/dashboard/types'
import { useDashboardOverview } from './features/dashboard/useDashboardOverview'

const navigation = [
  { label: 'Dashboard', icon: Activity, active: true },
  { label: 'Claims', icon: Document, active: false },
  { label: 'Admin Config', icon: SettingsAdjust, active: false },
]

const capabilityTone: Record<CapabilityState, 'success' | 'warning' | 'default'> = {
  ready: 'success',
  mock: 'default',
  warning: 'warning',
}

function App() {
  const { data, error, isPending } = useDashboardOverview()

  return (
    <main className="min-h-[100dvh] bg-slate-100 text-slate-950">
      <div className="grid min-h-[100dvh] grid-cols-1 lg:grid-cols-[272px_minmax(0,1fr)]">
        <aside className="border-b border-slate-200 bg-slate-950 px-5 py-5 text-white lg:border-b-0 lg:border-r lg:border-slate-800">
          <div className="flex h-full flex-col gap-6">
            <div className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-lg bg-blue-500 text-white">
                <Ai size={22} />
              </div>
              <div>
                <div className="text-sm font-semibold">Claim Assistant</div>
                <div className="text-xs text-slate-400">Insurance PoC</div>
              </div>
            </div>

            <nav className="grid grid-cols-3 gap-2 lg:grid-cols-1" aria-label="Primary navigation">
              {navigation.map((item) => {
                const Icon = item.icon

                return (
                  <a
                    aria-current={item.active ? 'page' : undefined}
                    className={[
                      'flex min-h-11 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors lg:justify-start',
                      item.active
                        ? 'bg-blue-600 text-white shadow-sm'
                        : 'text-slate-300 hover:bg-slate-900 hover:text-white',
                    ].join(' ')}
                    href="#"
                    key={item.label}
                  >
                    <Icon size={18} />
                    <span>{item.label}</span>
                  </a>
                )
              })}
            </nav>

            {/* <div className="mt-auto hidden rounded-lg border border-slate-800 bg-slate-900 p-4 lg:block">
              <div className="mb-3 flex items-center gap-2 text-sm font-semibold text-slate-100">
                <CheckmarkOutline size={18} />
                Task 01 boundary
              </div>
              <p className="mb-4 text-sm leading-6 text-slate-400">
                Frontend shell only. Backend, Postgres and runtime configuration remain unchanged.
              </p>
              <Button className="w-full justify-between" size="sm" variant="primary">
                Login shell
                <Login size={16} />
              </Button>
            </div> */}
          </div>
        </aside>

        <section className="min-w-0 px-4 py-4 sm:px-6 lg:px-8">
          <div className="mx-auto grid max-w-[1440px] gap-6">
            <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 xl:flex-row xl:items-end xl:justify-between">
              <div>
                <p className="mb-2 text-sm font-semibold text-slate-500">PoC application shell</p>
                <h1 className="max-w-3xl text-3xl font-semibold tracking-normal text-slate-950 sm:text-4xl">
                  AI-assisted claim review workspace
                </h1>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
                  A focused operating surface for upload intake, damage analysis, policy review and
                  adjuster decisions.
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                <Chip color="success" variant="soft">
                  Backend health ready
                </Chip>
                <Chip color="default" variant="soft">
                  Mock adapters active
                </Chip>
              </div>
            </header>

            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard
                icon={Document}
                label="Open claims"
                loading={isPending}
                value={data?.metrics.openClaims}
              />
              <MetricCard
                icon={WarningAlt}
                label="Review required"
                loading={isPending}
                tone="warning"
                value={data?.metrics.reviewRequired}
              />
              <MetricCard
                icon={Activity}
                label="Avg model latency"
                loading={isPending}
                value={data?.metrics.avgModelLatency}
              />
              <MetricCard
                icon={CheckmarkOutline}
                label="AI conclusions"
                loading={isPending}
                tone="success"
                value={data?.metrics.aiConclusionReady}
              />
            </div>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
              <div className="grid gap-6">
                <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
                  <Card.Header className="flex flex-col gap-3 border-b border-slate-100 px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <Card.Title className="text-lg text-slate-950">Claim work queue</Card.Title>
                      <Card.Description className="text-sm text-slate-500">
                        Prioritized claim files ready for intake, AI review and adjuster action.
                      </Card.Description>
                    </div>
                    <Button className="w-full sm:w-auto" size="sm" variant="primary">
                      <CloudUpload size={17} />
                      New claim
                    </Button>
                  </Card.Header>
                  <Card.Content className="p-5">
                    {isPending ? <QueueSkeleton /> : null}
                    {error ? <InlineError message="Dashboard data could not be loaded." /> : null}
                    {data && data.claims.length > 0 ? <ClaimQueueTable claims={data.claims} /> : null}
                    {data && data.claims.length === 0 ? (
                      <EmptyState>
                        <div className="text-sm font-semibold text-slate-950">No claims in the queue</div>
                        <p className="mt-1 text-sm text-slate-500">
                          Upload claim evidence to create the first review file.
                        </p>
                      </EmptyState>
                    ) : null}
                  </Card.Content>
                </Card>

                <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
                  <Card.Header className="border-b border-slate-100 px-5 py-4">
                    <Card.Title className="text-lg text-slate-950">Review flow baseline</Card.Title>
                    <Card.Description className="text-sm text-slate-500">
                      The shell keeps the future workflow visible without implementing later task scope.
                    </Card.Description>
                  </Card.Header>
                  <Card.Content className="grid gap-3 p-5 md:grid-cols-3">
                    {['Evidence intake', 'Damage analysis', 'Decision packet'].map((step) => (
                      <div className="rounded-lg border border-slate-200 bg-slate-50 p-4" key={step}>
                        <div className="mb-3 flex size-9 items-center justify-center rounded-lg bg-white text-blue-700 ring-1 ring-slate-200">
                          <ChevronRight size={18} />
                        </div>
                        <div className="text-sm font-semibold text-slate-950">{step}</div>
                        <p className="mt-2 text-sm leading-6 text-slate-600">
                          Reserved surface for the end-to-end claim flow in upcoming tasks.
                        </p>
                      </div>
                    ))}
                  </Card.Content>
                </Card>
              </div>

              <aside className="grid content-start gap-6">
                <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
                  <Card.Header className="border-b border-slate-100 px-5 py-4">
                    <Card.Title className="flex items-center gap-2 text-lg text-slate-950">
                      <ChartColumn size={20} />
                      Queue mix
                    </Card.Title>
                  </Card.Header>
                  <Card.Content className="h-64 p-5">
                    {data ? (
                      <ResponsiveContainer height="100%" width="100%">
                        <BarChart data={data.queueMix} margin={{ left: -24, right: 4, top: 8 }}>
                          <CartesianGrid stroke="#e2e8f0" vertical={false} />
                          <XAxis dataKey="name" fontSize={12} stroke="#64748b" tickLine={false} />
                          <YAxis allowDecimals={false} fontSize={12} stroke="#64748b" tickLine={false} />
                          <Tooltip cursor={{ fill: '#eff6ff' }} />
                          <Bar dataKey="value" fill="#2563eb" radius={[6, 6, 0, 0]} />
                        </BarChart>
                      </ResponsiveContainer>
                    ) : (
                      <Skeleton className="h-full rounded-lg" />
                    )}
                  </Card.Content>
                </Card>

                <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
                  <Card.Header className="border-b border-slate-100 px-5 py-4">
                    <Card.Title className="text-lg text-slate-950">Runtime readiness</Card.Title>
                  </Card.Header>
                  <Card.Content className="grid gap-3 p-5">
                    {(data?.capabilities ?? []).map((item) => (
                      <div
                        className="flex items-start justify-between gap-3 rounded-lg border border-slate-200 px-3 py-3"
                        key={item.name}
                      >
                        <div>
                          <div className="text-sm font-semibold text-slate-950">{item.name}</div>
                          <div className="text-xs text-slate-500">{item.mode}</div>
                        </div>
                        <Chip color={capabilityTone[item.state]} size="sm" variant="soft">
                          {item.state}
                        </Chip>
                      </div>
                    ))}
                    {isPending ? <Skeleton className="h-24 rounded-lg" /> : null}
                  </Card.Content>
                </Card>

                <Alert status="warning">
                  <Alert.Title>PoC safety boundary</Alert.Title>
                  <Alert.Description>
                    Sample data is isolated in the frontend repository layer. Connect real APIs only
                    through service boundaries in later tasks.
                  </Alert.Description>
                </Alert>
              </aside>
            </div>
          </div>
        </section>
      </div>
    </main>
  )
}

type MetricCardProps = {
  icon: typeof Document
  label: string
  loading: boolean
  tone?: 'default' | 'success' | 'warning'
  value?: number | string
}

function MetricCard({ icon: Icon, label, loading, tone = 'default', value }: MetricCardProps) {
  const toneClasses = {
    default: 'bg-blue-50 text-blue-700 ring-blue-100',
    success: 'bg-emerald-50 text-emerald-700 ring-emerald-100',
    warning: 'bg-amber-50 text-amber-700 ring-amber-100',
  }

  return (
    <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
      <Card.Content className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-sm font-medium text-slate-500">{label}</div>
            {loading ? (
              <Skeleton className="mt-3 h-8 w-24 rounded-lg" />
            ) : (
              <div className="mt-2 font-mono text-3xl font-semibold text-slate-950">{value}</div>
            )}
          </div>
          <div className={`flex size-10 items-center justify-center rounded-lg ring-1 ${toneClasses[tone]}`}>
            <Icon size={20} />
          </div>
        </div>
      </Card.Content>
    </Card>
  )
}

function QueueSkeleton() {
  return (
    <div className="grid gap-3">
      <Skeleton className="h-12 rounded-lg" />
      <Skeleton className="h-12 rounded-lg" />
      <Skeleton className="h-12 rounded-lg" />
    </div>
  )
}

function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 p-4 text-red-900">
      <ErrorOutline className="mt-0.5 shrink-0" size={18} />
      <div>
        <div className="text-sm font-semibold">Unable to load queue</div>
        <p className="mt-1 text-sm">{message}</p>
      </div>
    </div>
  )
}

export default App
