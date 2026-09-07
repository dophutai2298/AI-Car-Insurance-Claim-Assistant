import { useQuery } from '@tanstack/react-query'

import { getDashboardOverview } from './dashboardRepository'

export function useDashboardOverview() {
  return useQuery({
    queryKey: ['dashboard-overview'],
    queryFn: getDashboardOverview,
  })
}
