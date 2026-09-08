import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

import { getCurrentUser, login as requestLogin } from './authApi'
import type { AuthSession, LoginCredentials } from './types'

const STORAGE_KEY = 'claim-assistant-session'

type AuthContextValue = {
  session: AuthSession | null
  isInitializing: boolean
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

function readStoredSession(): AuthSession | null {
  const storedValue = sessionStorage.getItem(STORAGE_KEY)
  if (!storedValue) return null

  try {
    const session = JSON.parse(storedValue) as AuthSession
    if (!session.access_token || !session.user?.email || !session.user?.role) return null
    return session
  } catch {
    sessionStorage.removeItem(STORAGE_KEY)
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(readStoredSession)
  const [isInitializing, setIsInitializing] = useState(session !== null)

  useEffect(() => {
    if (!session) return

    let isCurrent = true
    getCurrentUser(session.access_token)
      .then((user) => {
        if (!isCurrent) return
        const verifiedSession = { ...session, user }
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(verifiedSession))
        setSession(verifiedSession)
      })
      .catch(() => {
        if (!isCurrent) return
        sessionStorage.removeItem(STORAGE_KEY)
        setSession(null)
      })
      .finally(() => {
        if (isCurrent) setIsInitializing(false)
      })

    return () => {
      isCurrent = false
    }
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      isInitializing,
      login: async (credentials) => {
        const nextSession = await requestLogin(credentials)
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(nextSession))
        setSession(nextSession)
      },
      logout: () => {
        sessionStorage.removeItem(STORAGE_KEY)
        setSession(null)
      },
    }),
    [isInitializing, session],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
