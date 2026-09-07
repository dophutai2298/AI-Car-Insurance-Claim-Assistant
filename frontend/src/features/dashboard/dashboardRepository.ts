import type { DashboardOverview } from './types'

const dashboardOverview: DashboardOverview = {
  metrics: {
    openClaims: 18,
    reviewRequired: 7,
    avgModelLatency: '2.4s',
    aiConclusionReady: 11,
  },
  claims: [
    {
      id: 'CLM-1048',
      claimant: 'Minh Tran',
      vehicle: '2024 Toyota Camry',
      status: 'REVIEW_REQUIRED',
      evidenceCount: 6,
      assessment: 'Replacement likely',
      updatedAt: '12 min ago',
    },
    {
      id: 'CLM-1047',
      claimant: 'Linh Pham',
      vehicle: '2022 Honda Civic',
      status: 'ANALYZING',
      evidenceCount: 4,
      assessment: 'Pending',
      updatedAt: '24 min ago',
    },
    {
      id: 'CLM-1042',
      claimant: 'Khoa Nguyen',
      vehicle: '2021 Mazda CX-5',
      status: 'AI_REJECTED',
      evidenceCount: 5,
      assessment: 'Manual inspection',
      updatedAt: '1 hr ago',
    },
    {
      id: 'CLM-1039',
      claimant: 'An Vo',
      vehicle: '2020 Ford Ranger',
      status: 'AI_APPROVED',
      evidenceCount: 3,
      assessment: 'Repair likely',
      updatedAt: '2 hr ago',
    },
  ],
  queueMix: [
    { name: 'Review', value: 7 },
    { name: 'Analyzing', value: 4 },
    { name: 'Approved', value: 5 },
    { name: 'Rejected', value: 2 },
  ],
  capabilities: [
    { name: 'Damage model adapter', mode: 'Mock service', state: 'mock' },
    { name: 'Postgres', mode: 'Local dev', state: 'ready' },
    { name: 'Part search', mode: 'Mock provider', state: 'mock' },
    { name: 'LLM', mode: 'Mock until OpenAI key is set', state: 'warning' },
  ],
}

export async function getDashboardOverview(): Promise<DashboardOverview> {
  return dashboardOverview
}
