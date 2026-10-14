import { useQuery } from "@tanstack/react-query";

import { useAuth } from "../auth/AuthProvider";
import { getDashboardOverview } from "./dashboardRepository";

export function useDashboardOverview() {
  const { session } = useAuth();

  return useQuery({
    queryKey: ["dashboard-overview", session?.user.role],
    queryFn: () =>
      getDashboardOverview(
        session!.access_token,
        session!.user.role as "ADMIN" | "ADJUSTER",
      ),
    enabled: Boolean(session && session.user.role !== "USER"),
  });
}
