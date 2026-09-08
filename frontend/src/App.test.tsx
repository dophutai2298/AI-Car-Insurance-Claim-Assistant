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
