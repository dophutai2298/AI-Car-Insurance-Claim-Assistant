import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { expect, test, vi } from 'vitest'

import { AppRoutes } from './App'
import { AuthProvider } from './features/auth/AuthProvider'

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

  await user.type(await screen.findByLabelText(/claimant name/i), 'Mai Nguyen')
  await user.type(screen.getByLabelText(/make/i), 'Toyota')
  await user.type(screen.getByLabelText(/model/i), 'Camry')
  await user.type(screen.getByLabelText(/year/i), '2022')
  await user.click(screen.getByRole('button', { name: /create claim/i }))

  expect(await screen.findByRole('heading', { name: /claim clm-000042/i })).toBeVisible()
  expect(screen.getByText('Toyota Camry')).toBeVisible()
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
