import type { VehicleManufacturer } from './types'

export class VehicleMakesApiError extends Error {}

export async function getVehicleManufacturers(accessToken: string): Promise<VehicleManufacturer[]> {
  const response = await fetch('/api/vehicle-makes', { headers: { Authorization: `Bearer ${accessToken}` } })
  const body: unknown = await response.json()
  if (!response.ok) throw new VehicleMakesApiError('Unable to load vehicle manufacturers')
  return body as VehicleManufacturer[]
}
