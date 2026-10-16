import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";

import { getCurrentUser, login as requestLogin } from "./authApi";
import type { AuthSession, LoginCredentials } from "./types";

const STORAGE_KEY = "claim-assistant-session";

type AuthContextValue = {
  session: AuthSession | null;
  isInitializing: boolean;
  login: (credentials: LoginCredentials) => Promise<AuthSession>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredSession(): AuthSession | null {
  const storedValue = sessionStorage.getItem(STORAGE_KEY);
  if (!storedValue) return null;

  try {
    const session = JSON.parse(storedValue) as AuthSession;
    if (!session.access_token || !session.user?.email || !session.user?.role)
      return null;
    return session;
  } catch {
    sessionStorage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [session, setSession] = useState<AuthSession | null>(readStoredSession);
  const [isInitializing, setIsInitializing] = useState(session !== null);

  useEffect(() => {
    if (!session) return;

    let isCurrent = true;
    getCurrentUser(session.access_token)
      .then((user) => {
        if (!isCurrent) return;
        if (
          user.email !== session.user.email ||
          user.role !== session.user.role
        )
          queryClient.clear();
        const verifiedSession = { ...session, user };
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(verifiedSession));
        setSession(verifiedSession);
      })
      .catch(() => {
        if (!isCurrent) return;
        queryClient.clear();
        sessionStorage.removeItem(STORAGE_KEY);
        setSession(null);
      })
      .finally(() => {
        if (isCurrent) setIsInitializing(false);
      });

    return () => {
      isCurrent = false;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      isInitializing,
      login: async (credentials) => {
        const nextSession = await requestLogin(credentials);
        queryClient.clear();
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(nextSession));
        setSession(nextSession);
        return nextSession;
      },
      logout: () => {
        queryClient.clear();
        sessionStorage.removeItem(STORAGE_KEY);
        setSession(null);
      },
    }),
    [isInitializing, queryClient, session],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
