import { useQuery } from '@tanstack/react-query'

import { useAuth } from '../auth/AuthProvider'
import { getVehicleManufacturers } from './vehicleMakesApi'

export const vehicleMakesKey = ['vehicle-makes'] as const

export function useVehicleMakes() {
  const { session } = useAuth()
  return useQuery({
    queryKey: vehicleMakesKey,
    queryFn: () => getVehicleManufacturers(session!.access_token),
    enabled: Boolean(session),
  })
}
