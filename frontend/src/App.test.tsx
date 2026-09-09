import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { expect, test, vi } from 'vitest'

import { AppRoutes } from './App'
import { AuthProvider } from './features/auth/AuthProvider'
import type { AssessmentRuleConfiguration } from './features/admin/types'
import type { ClaimDetail, EvidenceCategory, EvidenceItem } from './features/claims/types'

const adminSession = {
  access_token: 'admin-token',
  token_type: 'bearer',
  user: { email: 'admin@example.com', full_name: 'Demo Admin', role: 'ADMIN' },
}

const adjusterSession = {
  access_token: 'adjuster-token',
  token_type: 'bearer',
  user: { email: 'adjuster@example.com', full_name: 'Demo Adjuster', role: 'ADJUSTER' },
}

function renderRoute(path: string) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

test('unauthenticated user is redirected to login', async () => {
  renderRoute('/dashboard')

  expect(await screen.findByRole('heading', { name: /sign in to claim assistant/i })).toBeVisible()
})

test('admin can log in and land on dashboard with admin navigation', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(adminSession), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
  const user = userEvent.setup()
  renderRoute('/login')

  await user.type(screen.getByLabelText(/email/i), 'admin@example.com')
  await user.type(screen.getByLabelText(/password/i), 'Admin123!')
  await user.click(screen.getByRole('button', { name: /sign in/i }))

  expect(await screen.findByRole('heading', { name: /claim review workspace/i })).toBeVisible()
  expect(screen.getByRole('link', { name: /admin config/i })).toBeVisible()
  expect(sessionStorage.getItem('claim-assistant-session')).toContain('admin-token')
})

test('adjuster cannot open the admin route', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(adjusterSession.user), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
  sessionStorage.setItem('claim-assistant-session', JSON.stringify(adjusterSession))
  renderRoute('/admin')

  expect(await screen.findByRole('heading', { name: /access restricted/i })).toBeVisible()
  expect(screen.queryByRole('link', { name: /admin config/i })).not.toBeInTheDocument()
})

test('server role overrides an admin role fabricated in browser storage', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify(adjusterSession.user), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
  sessionStorage.setItem(
    'claim-assistant-session',
    JSON.stringify({ ...adjusterSession, user: adminSession.user }),
  )
  renderRoute('/admin')

  expect(await screen.findByRole('heading', { name: /access restricted/i })).toBeVisible()
})

test('invalid credentials display the safe API error', async () => {
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify({ detail: 'Invalid email or password' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' },
    }),
  )
  const user = userEvent.setup()
  renderRoute('/login')

  await user.type(screen.getByLabelText(/email/i), 'admin@example.com')
  await user.type(screen.getByLabelText(/password/i), 'incorrect')
  await user.click(screen.getByRole('button', { name: /sign in/i }))

  expect(await screen.findByText('Invalid email or password')).toBeVisible()
})

test('claims route renders the dedicated claim table', async () => {
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
    if (String(input).endsWith('/api/auth/me')) return new Response(JSON.stringify(adjusterSession.user))
    return new Response(JSON.stringify([{
      id: 'CLM-000071',
      claimant_name: 'Mai Nguyen',
      vehicle_summary: '2022 Toyota Camry',
      status: 'DRAFT',
      updated_at: '2026-09-08T00:00:00Z',
    }]))
  })
  sessionStorage.setItem('claim-assistant-session', JSON.stringify(adjusterSession))
  renderRoute('/claims')

  expect(await screen.findByRole('heading', { name: /claim cases/i })).toBeVisible()
  expect(await screen.findByRole('table')).toBeVisible()
  expect(screen.getByRole('link', { name: /clm-000071/i })).toBeVisible()
})

test('adjuster can create a claim and open its detail', async () => {
  const createdClaim = {
    id: 'CLM-000042',
    claimant_name: 'Mai Nguyen',
    vehicle: {
      make: 'Toyota',
      model: 'Camry',
      year: 2022,
      license_plate: '51H-123.45',
      vin: '4T1G11AKXNU123456',
    },
    status: 'DRAFT',
    created_at: '2026-09-08T00:00:00Z',
    updated_at: '2026-09-08T00:00:00Z',
  }
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    if (String(input).endsWith('/api/auth/me')) {
      return new Response(JSON.stringify(adjusterSession.user), { status: 200 })
    }
    if (String(input).endsWith('/api/claims') && init?.method === 'POST') {
      return new Response(JSON.stringify(createdClaim), { status: 201 })
    }
    if (String(input).endsWith('/api/claims/CLM-000042')) {
      return new Response(JSON.stringify(createdClaim), { status: 200 })
    }
    return new Response(JSON.stringify([]), { status: 200 })
  })
  sessionStorage.setItem('claim-assistant-session', JSON.stringify(adjusterSession))
  const user = userEvent.setup()
  renderRoute('/claims/new')

  expect(await screen.findByRole('navigation', { name: /primary navigation/i })).toBeVisible()
  expect(within(screen.getByRole('navigation', { name: /primary navigation/i })).getByRole('link', { name: /^claims$/i })).toBeVisible()
  await user.type(await screen.findByLabelText(/claimant name/i), 'Mai Nguyen')
  await user.type(screen.getByLabelText(/make/i), 'Toyota')
  await user.type(screen.getByLabelText(/model/i), 'Camry')
  await user.type(screen.getByLabelText(/year/i), '2022')
  await user.click(screen.getByRole('button', { name: /create claim/i }))

  expect(await screen.findByRole('heading', { name: /claim clm-000042/i })).toBeVisible()
  expect(screen.getByText('Toyota Camry')).toBeVisible()
  expect(screen.getByRole('navigation', { name: /primary navigation/i })).toBeVisible()
})

test('adjuster can start the safe AI review lifecycle from claim detail', async () => {
  const draftClaim = {
    id: 'CLM-000051',
    claimant_name: 'Mai Nguyen',
    vehicle: { make: 'Toyota', model: 'Camry', year: 2022, license_plate: null, vin: null },
    status: 'DRAFT',
    created_at: '2026-09-08T00:00:00Z',
    updated_at: '2026-09-08T00:00:00Z',
  }
  let currentClaim = draftClaim
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    if (String(input).endsWith('/api/auth/me')) return new Response(JSON.stringify(adjusterSession.user))
    if (String(input).endsWith('/status') && init?.method === 'PATCH') {
      currentClaim = { ...draftClaim, status: 'ANALYZING' }
    }
    return new Response(JSON.stringify(currentClaim))
  })
  sessionStorage.setItem('claim-assistant-session', JSON.stringify(adjusterSession))
  const user = userEvent.setup()
  renderRoute('/claims/CLM-000051')

  await user.click(await screen.findByRole('button', { name: /begin ai analysis/i }))

  expect(await screen.findByText('Analyzing')).toBeVisible()
})

test('adjuster uploads evidence with a selected category from claim detail', async () => {
  let currentClaim = {
    id: 'CLM-000061',
    claimant_name: 'Mai Nguyen',
    vehicle: { make: 'Toyota', model: 'Camry', year: 2022, license_plate: null, vin: null },
    status: 'DRAFT',
    created_at: '2026-09-08T00:00:00Z',
    updated_at: '2026-09-08T00:00:00Z',
    evidence: [] as EvidenceItem[],
  }
  let uploadedCategory = ''
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    if (String(input).endsWith('/api/auth/me')) return new Response(JSON.stringify(adjusterSession.user))
    if (String(input).endsWith('/evidence') && init?.method === 'POST') {
      uploadedCategory = (init.body as FormData).get('categories') as string
      currentClaim = {
        ...currentClaim,
        evidence: [{
          id: 1,
          category: uploadedCategory as EvidenceCategory,
          original_filename: 'policy.pdf',
          content_type: 'application/pdf',
          file_size: 12,
          uploaded_at: '2026-09-08T00:00:00Z',
          content_url: '/api/claims/CLM-000061/evidence/1/content',
        }],
      }
    }
    return new Response(JSON.stringify(currentClaim))
  })
  sessionStorage.setItem('claim-assistant-session', JSON.stringify(adjusterSession))
  const user = userEvent.setup()
  renderRoute('/claims/CLM-000061')

  await user.upload(await screen.findByLabelText(/select evidence files/i), new File(['document'], 'policy.pdf', { type: 'application/pdf' }))
  await user.selectOptions(screen.getByLabelText(/category for policy.pdf/i), 'INSURANCE_POLICY')
  await user.click(screen.getByRole('button', { name: /upload evidence/i }))

  expect(await screen.findByText('Insurance policies')).toBeVisible()
  expect(uploadedCategory).toBe('INSURANCE_POLICY')
})

test('adjuster can run damage analysis and review the no-damage warning', async () => {
  const damageImage: EvidenceItem = {
    id: 1,
    category: 'VEHICLE_DAMAGE_IMAGE',
    original_filename: 'no-damage.jpg',
    content_type: 'image/jpeg',
    file_size: 20,
    uploaded_at: '2026-09-08T00:00:00Z',
    content_url: '/api/claims/CLM-000071/evidence/1/content',
  }
  let currentClaim: ClaimDetail = {
    id: 'CLM-000071',
    claimant_name: 'Mai Nguyen',
    vehicle: { make: 'Toyota', model: 'Camry', year: 2022, license_plate: null, vin: null },
    status: 'ANALYZING',
    created_at: '2026-09-08T00:00:00Z',
    updated_at: '2026-09-08T00:00:00Z',
    evidence: [damageImage],
    latest_damage_analysis: null,
  }
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    if (String(input).endsWith('/api/auth/me')) return new Response(JSON.stringify(adjusterSession.user))
    if (String(input).endsWith('/damage-analysis') && init?.method === 'POST') {
      currentClaim = {
        ...currentClaim,
        status: 'REVIEW_REQUIRED',
        latest_damage_analysis: {
          id: 'DA-000001', assessment: 'NO_DAMAGE', detections: [],
          warning: 'No significant vehicle damage was detected. This does not guarantee the vehicle is undamaged.',
          rules: { confidence_threshold: 0.7, repair_max_percentage: 40, replacement_min_percentage: 60 },
          reference_price_status: 'NOT_REQUESTED',
          reference_prices: [],
          copilot_conclusion: {
            status: 'FALLBACK',
            recommendation: 'MANUAL_ADJUSTER_REVIEW',
            summary: 'No normalized damage finding supports a no-damage assessment. An adjuster must review this case before any final decision.',
            fallback_summary: 'No normalized damage finding supports a no-damage assessment. An adjuster must review this case before any final decision.',
            failure_reason: null,
            provider_model: null,
            findings: [],
            warnings: ['No significant vehicle damage was detected. This does not guarantee the vehicle is undamaged.'],
            reference_prices: [],
          },
          created_at: '2026-09-08T00:01:00Z',
        },
      }
      return new Response(JSON.stringify(currentClaim.latest_damage_analysis))
    }
    return new Response(JSON.stringify(currentClaim))
  })
  sessionStorage.setItem('claim-assistant-session', JSON.stringify(adjusterSession))
  const user = userEvent.setup()
  renderRoute('/claims/CLM-000071')

  await user.click(await screen.findByRole('button', { name: /run analysis/i }))

  expect((await screen.findAllByText('No significant damage')).length).toBeGreaterThan(0)
  expect(await screen.findByText(/does not guarantee/i)).toBeVisible()
  expect(await screen.findByText('Reference OEM/original part price')).toBeVisible()
  expect(await screen.findByText(/not requested\. reference price lookup/i)).toBeVisible()
  expect(await screen.findByText('AI copilot conclusion')).toBeVisible()
  expect(await screen.findByText('Demo fallback')).toBeVisible()
})

test('admin can update global assessment rules from the configuration page', async () => {
  let configuration: AssessmentRuleConfiguration = {
    values: { confidence_threshold: 0.7, repair_max_percentage: 40, replacement_min_percentage: 60 },
    updated_by: null,
    updated_at: '2026-09-08T00:00:00Z',
  }
  let savedValues: unknown = null
  vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
    if (String(input).endsWith('/api/auth/me')) return new Response(JSON.stringify(adminSession.user))
    if (String(input).endsWith('/assessment-rules/history')) return new Response(JSON.stringify([]))
    if (String(input).endsWith('/assessment-rules') && init?.method === 'PUT') {
      savedValues = JSON.parse(init.body as string)
      configuration = { ...configuration, values: savedValues as typeof configuration.values, updated_by: 'admin@example.com' }
      return new Response(JSON.stringify(configuration))
    }
    return new Response(JSON.stringify(configuration))
  })
  sessionStorage.setItem('claim-assistant-session', JSON.stringify(adminSession))
  const user = userEvent.setup()
  renderRoute('/admin')

  await user.clear(await screen.findByLabelText(/confidence threshold/i))
  await user.type(screen.getByLabelText(/confidence threshold/i), '0.8')
  await user.click(screen.getByRole('button', { name: /save rules/i }))

  expect(savedValues).toEqual({ confidence_threshold: 0.8, repair_max_percentage: 40, replacement_min_percentage: 60 })
  expect(await screen.findByText(/last changed by admin@example.com/i)).toBeVisible()
})
