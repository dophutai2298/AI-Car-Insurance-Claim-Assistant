import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router";

import { useAuth } from "./AuthProvider";
import type { UserRole } from "./types";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isInitializing, session } = useAuth();
  const location = useLocation();

  if (isInitializing) {
    return (
      <main className="flex min-h-dvh items-center justify-center bg-slate-100 text-sm text-slate-600">
        Checking session...
      </main>
    );
  }

  if (!session)
    return <Navigate replace state={{ from: location.pathname }} to="/login" />;
  return children;
}

export function RoleRoute({
  children,
  fallback,
  role,
}: {
  children: ReactNode;
  fallback: ReactNode;
  role: UserRole;
}) {
  const { session } = useAuth();
  return session?.user.role === role ? children : fallback;
}
