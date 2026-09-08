import { useQuery } from '@tanstack/react-query'

import { useAuth } from '../auth/AuthProvider'
import { getDashboardOverview } from './dashboardRepository'

export function useDashboardOverview() {
  const { session } = useAuth()

  return useQuery({
    queryKey: ['dashboard-overview'],
    queryFn: () => getDashboardOverview(session!.access_token),
    enabled: Boolean(session),
  })
}
