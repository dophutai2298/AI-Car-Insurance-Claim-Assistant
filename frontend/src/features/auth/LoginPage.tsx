import { useState, type FormEvent } from 'react'
import { ArrowRight, CarFront, Locked, Security } from '@carbon/icons-react'
import { Alert, Button, Card, Input, Label, TextField } from '@heroui/react'
import { Navigate, useLocation, useNavigate } from 'react-router'

import { AuthApiError } from './authApi'
import { useAuth } from './AuthProvider'

export function LoginPage() {
  const { login, session } = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isPending, setIsPending] = useState(false)

  if (session) return <Navigate replace to="/dashboard" />

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setIsPending(true)
    try {
      await login({ email, password })
      const requestedPath = (location.state as { from?: string } | null)?.from
      navigate(requestedPath && requestedPath !== '/login' ? requestedPath : '/dashboard', {
        replace: true,
      })
    } catch (caughtError) {
      setError(caughtError instanceof AuthApiError ? caughtError.message : 'Unable to sign in')
    } finally {
      setIsPending(false)
    }
  }

  return (
    <main className="grid min-h-dvh bg-slate-100 text-slate-950 lg:grid-cols-[minmax(320px,0.82fr)_minmax(480px,1.18fr)]">
      <section className="hidden bg-slate-950 px-10 py-12 text-white lg:flex lg:flex-col lg:justify-between xl:px-16">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-lg bg-blue-500">
            <CarFront size={22} />
          </div>
          <div>
            <div className="text-sm font-semibold">Claim Assistant</div>
            <div className="text-xs text-slate-400">Insurance PoC</div>
          </div>
        </div>

        <div className="max-w-lg">
          <div className="mb-6 flex size-12 items-center justify-center rounded-lg border border-slate-700 bg-slate-900 text-blue-300">
            <Security size={24} />
          </div>
          <p className="text-sm font-semibold text-blue-300">Secure adjuster workspace</p>
          <h2 className="mt-3 text-3xl font-semibold leading-tight tracking-normal xl:text-4xl">
            Review evidence with clear human control.
          </h2>
          <p className="mt-5 max-w-md text-sm leading-6 text-slate-400">
            Vehicle damage findings, supporting documents and AI conclusions stay organized in one
            operational workspace.
          </p>
        </div>

        <p className="text-xs text-slate-500">Authorized local demonstration access only</p>
      </section>

      <section className="flex min-h-dvh items-center justify-center px-5 py-10 sm:px-8 lg:min-h-0">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <div className="flex size-10 items-center justify-center rounded-lg bg-blue-600 text-white">
              <CarFront size={22} />
            </div>
            <div>
              <div className="text-sm font-semibold">Claim Assistant</div>
              <div className="text-xs text-slate-500">Insurance PoC</div>
            </div>
          </div>

          <Card className="rounded-lg border border-slate-200 bg-white shadow-sm">
            <Card.Header className="border-b border-slate-100 px-6 py-5">
              <div className="flex size-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700 ring-1 ring-blue-100">
                <Locked size={20} />
              </div>
              <div className="mt-4">
                <Card.Title className="text-2xl text-slate-950">Sign in to Claim Assistant</Card.Title>
                <Card.Description className="mt-2 text-sm text-slate-500">
                  Use your Admin or Adjuster account to continue.
                </Card.Description>
              </div>
            </Card.Header>
            <Card.Content className="p-6">
              <form className="grid gap-5" onSubmit={handleSubmit}>
                {error ? (
                  <Alert status="danger">
                    <Alert.Title>Sign-in failed</Alert.Title>
                    <Alert.Description>{error}</Alert.Description>
                  </Alert>
                ) : null}

                <TextField fullWidth isRequired name="email" type="email">
                  <Label>Email</Label>
                  <Input
                    autoComplete="email"
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="name@company.com"
                    value={email}
                  />
                </TextField>
                <TextField fullWidth isRequired name="password" type="password">
                  <Label>Password</Label>
                  <Input
                    autoComplete="current-password"
                    onChange={(event) => setPassword(event.target.value)}
                    value={password}
                  />
                </TextField>
                <Button className="mt-1 w-full" isPending={isPending} type="submit" variant="primary">
                  Sign in
                  <ArrowRight size={18} />
                </Button>
              </form>
            </Card.Content>
          </Card>
        </div>
      </section>
    </main>
  )
}
